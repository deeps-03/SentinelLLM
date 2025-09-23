#!/usr/bin/env python3
"""
Loki to Kafka Forwarder Service
High-performance service to forward logs from Loki to Kafka with intelligent batching
"""

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
import os
import pickle
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ForwarderMetrics:
    """Metrics tracking for the forwarder service"""
    logs_processed: int = 0
    logs_forwarded: int = 0
    errors: int = 0
    batches_processed: int = 0
    start_time: float = 0
    last_checkpoint: str = ""

class TokenBucket:
    """Token bucket for rate limiting"""
    
    def __init__(self, rate: float, capacity: float):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
    
    def can_consume(self, tokens: int = 1) -> bool:
        """Check if we can consume tokens"""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

class LokiKafkaForwarder:
    """High-performance Loki to Kafka forwarder with intelligent batching"""
    
    def __init__(self, 
                 loki_url: str = "http://loki:3100",
                 kafka_servers: str = "kafka:9092",
                 kafka_topic: str = "raw-logs",
                 batch_size: int = 100,
                 rate_limit: float = 1000.0,  # logs per second
                 query_interval: int = 10):   # seconds
        
        self.loki_url = loki_url.rstrip('/')
        self.kafka_servers = kafka_servers
        self.kafka_topic = kafka_topic
        self.batch_size = batch_size
        self.query_interval = query_interval
        
        # Rate limiting
        self.rate_limiter = TokenBucket(rate_limit, rate_limit * 2)  # 2 second burst
        
        # Kafka producer
        self.kafka_producer = None
        
        # Metrics
        self.metrics = ForwarderMetrics()
        self.metrics.start_time = time.time()
        
        # State management
        self.checkpoint_file = "/tmp/loki_forwarder_checkpoint.pkl"
        self.last_query_time = self.load_checkpoint()
        
        # HTTP session
        self.session = None
        
    def load_checkpoint(self) -> str:
        """Load the last query timestamp from checkpoint"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'rb') as f:
                    data = pickle.load(f)
                    checkpoint_time = data.get('last_query_time', '')
                    logger.info(f"Loaded checkpoint: {checkpoint_time}")
                    return checkpoint_time
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
        
        # Default to 1 minute ago
        default_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        logger.info(f"Using default checkpoint: {default_time}")
        return default_time
    
    def save_checkpoint(self, timestamp: str):
        """Save the current query timestamp"""
        try:
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump({
                    'last_query_time': timestamp,
                    'saved_at': datetime.now(timezone.utc).isoformat()
                }, f)
            self.metrics.last_checkpoint = timestamp
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def setup_kafka_producer(self):
        """Initialize Kafka producer with optimized settings"""
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=[self.kafka_servers],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                # Optimization for high throughput
                batch_size=16384,  # 16KB batches
                linger_ms=5,       # Wait 5ms to batch messages
                buffer_memory=33554432,  # 32MB buffer
                compression_type='gzip',
                retries=3,
                acks='1'  # Wait for leader acknowledgment
            )
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    async def setup_http_session(self):
        """Initialize HTTP session for Loki queries"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close_http_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def query_loki(self, start_time: str, end_time: str) -> List[Dict]:
        """Query Loki for logs in the specified time range"""
        query = '{job=~".+"}'  # Query all jobs
        
        params = {
            'query': query,
            'start': start_time,
            'end': end_time,
            'limit': 5000,  # High limit for batch processing
            'direction': 'forward'
        }
        
        try:
            async with self.session.get(
                f"{self.loki_url}/loki/api/v1/query_range",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logs = []
                    
                    # Parse Loki response format
                    for stream in data.get('data', {}).get('result', []):
                        stream_labels = stream.get('stream', {})
                        values = stream.get('values', [])
                        
                        for timestamp, log_line in values:
                            log_entry = {
                                'timestamp': timestamp,
                                'message': log_line,
                                'labels': stream_labels,
                                'source': stream_labels.get('source', 'loki'),
                                'level': stream_labels.get('level', 'info'),
                                'forwarded_at': datetime.now(timezone.utc).isoformat()
                            }
                            logs.append(log_entry)
                    
                    logger.debug(f"Retrieved {len(logs)} logs from Loki")
                    return logs
                else:
                    logger.error(f"Loki query failed: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error querying Loki: {e}")
            self.metrics.errors += 1
            return []
    
    def send_batch_to_kafka(self, logs: List[Dict]) -> bool:
        """Send a batch of logs to Kafka"""
        if not logs:
            return True
            
        try:
            futures = []
            for log in logs:
                future = self.kafka_producer.send(self.kafka_topic, value=log)
                futures.append(future)
            
            # Wait for all sends to complete
            for future in futures:
                try:
                    future.get(timeout=10)  # 10 second timeout per message
                except KafkaError as e:
                    logger.error(f"Failed to send message to Kafka: {e}")
                    self.metrics.errors += 1
                    return False
            
            self.metrics.logs_forwarded += len(logs)
            self.metrics.batches_processed += 1
            logger.info(f"Successfully sent batch of {len(logs)} logs to Kafka")
            return True
            
        except Exception as e:
            logger.error(f"Error sending batch to Kafka: {e}")
            self.metrics.errors += 1
            return False
    
    async def process_logs_batch(self, logs: List[Dict]) -> bool:
        """Process a batch of logs with rate limiting"""
        if not logs:
            return True
        
        # Apply rate limiting
        if not self.rate_limiter.can_consume(len(logs)):
            logger.debug(f"Rate limit reached, delaying batch of {len(logs)} logs")
            await asyncio.sleep(1)  # Wait 1 second before retrying
            return False
        
        # Send to Kafka
        success = self.send_batch_to_kafka(logs)
        self.metrics.logs_processed += len(logs)
        
        return success
    
    async def run_forwarding_cycle(self):
        """Run one cycle of log forwarding"""
        current_time = datetime.now(timezone.utc)
        end_time = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Query logs from last checkpoint to now
        logs = await self.query_loki(self.last_query_time, end_time)
        
        if logs:
            # Process logs in batches
            for i in range(0, len(logs), self.batch_size):
                batch = logs[i:i + self.batch_size]
                success = await self.process_logs_batch(batch)
                
                if not success:
                    logger.warning(f"Failed to process batch {i//self.batch_size + 1}")
                    # Continue with next batch instead of failing completely
        
        # Update checkpoint
        self.last_query_time = end_time
        self.save_checkpoint(end_time)
    
    def log_metrics(self):
        """Log current metrics"""
        uptime = time.time() - self.metrics.start_time
        rate = self.metrics.logs_processed / uptime if uptime > 0 else 0
        
        logger.info(f"Metrics - Processed: {self.metrics.logs_processed}, "
                   f"Forwarded: {self.metrics.logs_forwarded}, "
                   f"Errors: {self.metrics.errors}, "
                   f"Rate: {rate:.1f} logs/sec, "
                   f"Batches: {self.metrics.batches_processed}")
    
    async def run(self):
        """Main run loop"""
        logger.info("Starting Loki to Kafka forwarder...")
        
        # Initialize components
        self.setup_kafka_producer()
        await self.setup_http_session()
        
        try:
            while True:
                cycle_start = time.time()
                
                await self.run_forwarding_cycle()
                
                # Log metrics every 10 cycles
                if self.metrics.batches_processed % 10 == 0:
                    self.log_metrics()
                
                # Calculate sleep time to maintain interval
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, self.query_interval - cycle_duration)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    logger.warning(f"Cycle took {cycle_duration:.1f}s, longer than interval {self.query_interval}s")
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            # Cleanup
            if self.kafka_producer:
                self.kafka_producer.close()
            await self.close_http_session()
            self.log_metrics()
            logger.info("Forwarder stopped")

async def main():
    # Configuration from environment variables
    loki_url = os.getenv('LOKI_URL', 'http://loki:3100')
    kafka_servers = os.getenv('KAFKA_SERVERS', 'kafka:9092')
    kafka_topic = os.getenv('KAFKA_TOPIC', 'raw-logs')
    batch_size = int(os.getenv('BATCH_SIZE', '100'))
    rate_limit = float(os.getenv('RATE_LIMIT', '1000'))
    query_interval = int(os.getenv('QUERY_INTERVAL', '10'))
    
    logger.info(f"Configuration:")
    logger.info(f"  Loki URL: {loki_url}")
    logger.info(f"  Kafka: {kafka_servers}")
    logger.info(f"  Topic: {kafka_topic}")
    logger.info(f"  Batch size: {batch_size}")
    logger.info(f"  Rate limit: {rate_limit} logs/sec")
    logger.info(f"  Query interval: {query_interval}s")
    
    forwarder = LokiKafkaForwarder(
        loki_url=loki_url,
        kafka_servers=kafka_servers,
        kafka_topic=kafka_topic,
        batch_size=batch_size,
        rate_limit=rate_limit,
        query_interval=query_interval
    )
    
    await forwarder.run()

if __name__ == "__main__":
    asyncio.run(main())