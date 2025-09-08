#!/usr/bin/env python3
"""
AWS CloudWatch Log Poller for Loki Integration
Enhanced version that sends logs to Loki instead of directly to Kafka
"""

import json
import time
import logging
import pickle
import os
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AWSLogPollerLoki:
    """Enhanced AWS CloudWatch log poller that sends logs to Loki"""
    
    def __init__(self, 
                 loki_url: str = "http://loki:3100",
                 aws_region: str = "us-east-1",
                 log_groups: List[str] = None,
                 poll_interval: int = 30,
                 batch_size: int = 100):
        
        self.loki_url = loki_url.rstrip('/')
        self.aws_region = aws_region
        self.log_groups = log_groups or []
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        
        # AWS CloudWatch client
        self.cloudwatch_logs = None
        
        # HTTP session for Loki
        self.session = None
        
        # Checkpoint management
        self.checkpoint_file = "/tmp/aws_loki_checkpoint.pkl"
        self.checkpoints = self.load_checkpoints()
        
        # Metrics
        self.metrics = {
            'logs_processed': 0,
            'logs_sent_to_loki': 0,
            'errors': 0,
            'start_time': time.time()
        }
    
    def setup_aws_client(self):
        """Initialize AWS CloudWatch Logs client"""
        try:
            self.cloudwatch_logs = boto3.client(
                'logs',
                region_name=self.aws_region
            )
            
            # Test connection
            self.cloudwatch_logs.describe_log_groups(limit=1)
            logger.info(f"AWS CloudWatch client initialized for region: {self.aws_region}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS client: {e}")
            raise
    
    async def setup_http_session(self):
        """Initialize HTTP session for Loki"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close_http_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    def load_checkpoints(self) -> Dict[str, int]:
        """Load checkpoint data from file"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'rb') as f:
                    checkpoints = pickle.load(f)
                    logger.info(f"Loaded checkpoints for {len(checkpoints)} log groups")
                    return checkpoints
        except Exception as e:
            logger.warning(f"Failed to load checkpoints: {e}")
        
        return {}
    
    def save_checkpoints(self):
        """Save checkpoint data to file"""
        try:
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(self.checkpoints, f)
        except Exception as e:
            logger.error(f"Failed to save checkpoints: {e}")
    
    def get_log_group_checkpoint(self, log_group: str) -> int:
        """Get the last processed timestamp for a log group"""
        if log_group not in self.checkpoints:
            # Default to 1 hour ago
            default_time = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000)
            self.checkpoints[log_group] = default_time
            logger.info(f"Initialized checkpoint for {log_group}: {default_time}")
        
        return self.checkpoints[log_group]
    
    def update_checkpoint(self, log_group: str, timestamp: int):
        """Update checkpoint for a log group"""
        self.checkpoints[log_group] = timestamp
        self.save_checkpoints()
    
    def fetch_logs_from_group(self, log_group: str, start_time: int, end_time: int) -> List[Dict]:
        """Fetch logs from a specific CloudWatch log group"""
        logs = []
        
        try:
            paginator = self.cloudwatch_logs.get_paginator('filter_log_events')
            
            page_iterator = paginator.paginate(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                PaginationConfig={
                    'MaxItems': 1000,  # High limit for better throughput
                    'PageSize': 100
                }
            )
            
            for page in page_iterator:
                events = page.get('events', [])
                
                for event in events:
                    # Convert CloudWatch event to Loki format
                    log_entry = {
                        'timestamp': str(event['timestamp'] * 1000000),  # Convert to nanoseconds
                        'message': event['message'],
                        'stream': {
                            'source': 'aws-cloudwatch',
                            'log_group': log_group,
                            'log_stream': event.get('logStreamName', 'unknown'),
                            'level': self.extract_log_level(event['message']),
                            'environment': 'production',
                            'service': 'aws-service'
                        }
                    }
                    logs.append(log_entry)
            
            logger.debug(f"Fetched {len(logs)} logs from {log_group}")
            
        except ClientError as e:
            logger.error(f"AWS API error for {log_group}: {e}")
            self.metrics['errors'] += 1
        except Exception as e:
            logger.error(f"Error fetching logs from {log_group}: {e}")
            self.metrics['errors'] += 1
        
        return logs
    
    def extract_log_level(self, message: str) -> str:
        """Extract log level from message"""
        message_upper = message.upper()
        if 'ERROR' in message_upper or 'FAIL' in message_upper:
            return 'error'
        elif 'WARN' in message_upper:
            return 'warning'
        elif 'INFO' in message_upper:
            return 'info'
        elif 'DEBUG' in message_upper:
            return 'debug'
        else:
            return 'info'
    
    async def send_logs_to_loki(self, logs: List[Dict]) -> bool:
        """Send logs to Loki in the expected format"""
        if not logs:
            return True
        
        # Group logs by stream labels for Loki
        streams = {}
        
        for log in logs:
            # Create stream key from labels
            stream_labels = log['stream']
            stream_key = json.dumps(stream_labels, sort_keys=True)
            
            if stream_key not in streams:
                streams[stream_key] = {
                    'stream': stream_labels,
                    'values': []
                }
            
            # Add timestamp and message
            streams[stream_key]['values'].append([
                log['timestamp'],
                log['message']
            ])
        
        # Prepare Loki payload
        payload = {
            'streams': list(streams.values())
        }
        
        try:
            async with self.session.post(
                f"{self.loki_url}/loki/api/v1/push",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 204:
                    self.metrics['logs_sent_to_loki'] += len(logs)
                    logger.debug(f"Successfully sent {len(logs)} logs to Loki")
                    return True
                else:
                    logger.error(f"Failed to send logs to Loki: HTTP {response.status}")
                    error_text = await response.text()
                    logger.error(f"Loki error response: {error_text}")
                    self.metrics['errors'] += 1
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending logs to Loki: {e}")
            self.metrics['errors'] += 1
            return False
    
    async def process_log_group(self, log_group: str):
        """Process logs from a single log group"""
        try:
            # Get time range
            start_time = self.get_log_group_checkpoint(log_group)
            end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
            
            if start_time >= end_time:
                logger.debug(f"No new logs for {log_group}")
                return
            
            # Fetch logs
            logs = self.fetch_logs_from_group(log_group, start_time, end_time)
            
            if logs:
                # Process logs in batches
                for i in range(0, len(logs), self.batch_size):
                    batch = logs[i:i + self.batch_size]
                    success = await self.send_logs_to_loki(batch)
                    
                    if success:
                        self.metrics['logs_processed'] += len(batch)
                    else:
                        logger.warning(f"Failed to send batch for {log_group}")
                        # Continue with next batch instead of failing completely
                
                # Update checkpoint to the latest timestamp
                if logs:
                    latest_timestamp = max(int(log['timestamp']) // 1000000 for log in logs)
                    self.update_checkpoint(log_group, latest_timestamp)
                    logger.info(f"Processed {len(logs)} logs from {log_group}")
            
        except Exception as e:
            logger.error(f"Error processing log group {log_group}: {e}")
            self.metrics['errors'] += 1
    
    async def run_polling_cycle(self):
        """Run one polling cycle for all log groups"""
        tasks = []
        
        for log_group in self.log_groups:
            task = asyncio.create_task(self.process_log_group(log_group))
            tasks.append(task)
        
        # Wait for all log groups to be processed
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def log_metrics(self):
        """Log current metrics"""
        uptime = time.time() - self.metrics['start_time']
        rate = self.metrics['logs_processed'] / uptime if uptime > 0 else 0
        
        logger.info(f"AWS Poller Metrics - Processed: {self.metrics['logs_processed']}, "
                   f"Sent to Loki: {self.metrics['logs_sent_to_loki']}, "
                   f"Errors: {self.metrics['errors']}, "
                   f"Rate: {rate:.1f} logs/sec")
    
    async def run(self):
        """Main run loop"""
        logger.info("Starting AWS CloudWatch log poller for Loki...")
        logger.info(f"Monitoring log groups: {self.log_groups}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Loki URL: {self.loki_url}")
        
        # Initialize components
        self.setup_aws_client()
        await self.setup_http_session()
        
        cycle_count = 0
        
        try:
            while True:
                cycle_start = time.time()
                
                await self.run_polling_cycle()
                
                cycle_count += 1
                
                # Log metrics every 10 cycles
                if cycle_count % 10 == 0:
                    self.log_metrics()
                
                # Calculate sleep time
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, self.poll_interval - cycle_duration)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    logger.warning(f"Polling cycle took {cycle_duration:.1f}s, longer than interval {self.poll_interval}s")
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            await self.close_http_session()
            self.log_metrics()
            logger.info("AWS log poller stopped")

async def main():
    # Configuration from environment variables
    loki_url = os.getenv('LOKI_URL', 'http://loki:3100')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    log_groups_str = os.getenv('AWS_LOG_GROUPS', '/aws/lambda/default')
    poll_interval = int(os.getenv('AWS_POLL_INTERVAL_SECONDS', '30'))
    batch_size = int(os.getenv('AWS_BATCH_SIZE', '100'))
    
    # Parse log groups
    log_groups = [lg.strip() for lg in log_groups_str.split(',') if lg.strip()]
    
    logger.info(f"Configuration:")
    logger.info(f"  Loki URL: {loki_url}")
    logger.info(f"  AWS Region: {aws_region}")
    logger.info(f"  Log Groups: {log_groups}")
    logger.info(f"  Poll Interval: {poll_interval}s")
    logger.info(f"  Batch Size: {batch_size}")
    
    poller = AWSLogPollerLoki(
        loki_url=loki_url,
        aws_region=aws_region,
        log_groups=log_groups,
        poll_interval=poll_interval,
        batch_size=batch_size
    )
    
    await poller.run()

if __name__ == "__main__":
    asyncio.run(main())