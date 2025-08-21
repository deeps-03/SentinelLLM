"""
AWS CloudWatch Logs Poller Service

This service connects to AWS CloudWatch Logs, polls real-time logs from specified
log groups, and pushes them into Kafka topic 'raw-logs'. It maintains checkpoints
to avoid duplicating logs after restarts.
"""

import os
import json
import time
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import pickle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AWSLogPoller:
    """AWS CloudWatch Logs polling service with checkpoint management."""
    
    def __init__(self):
        self.config = {
            'kafka_broker': os.getenv('KAFKA_BROKER', 'kafka:9093'),
            'kafka_topic': os.getenv('RAW_LOGS_TOPIC', 'raw-logs'),
            'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'log_groups': os.getenv('AWS_LOG_GROUPS', '').split(','),
            'poll_interval': int(os.getenv('AWS_POLL_INTERVAL_SECONDS', '30')),
            'checkpoint_file': '/app/checkpoints/aws_checkpoint.pkl',
            'max_retries': int(os.getenv('MAX_RETRIES', '5')),
            'retry_delay': int(os.getenv('RETRY_DELAY_SECONDS', '5'))
        }
        
        # Validate configuration
        self._validate_config()
        
        # Initialize clients
        self.cloudwatch_logs = None
        self.kafka_producer = None
        self.checkpoints = {}
        
        # Initialize services
        self._initialize_aws_client()
        self._initialize_kafka_producer()
        self._load_checkpoints()
    
    def _validate_config(self):
        """Validate required configuration parameters."""
        required_vars = [
            'aws_access_key_id', 'aws_secret_access_key', 'log_groups'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not self.config.get(var):
                missing_vars.append(var.upper())
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Clean up log groups list
        self.config['log_groups'] = [
            group.strip() for group in self.config['log_groups'] 
            if group.strip()
        ]
        
        if not self.config['log_groups']:
            raise ValueError("No valid log groups specified in AWS_LOG_GROUPS")
    
    def _initialize_aws_client(self):
        """Initialize AWS CloudWatch Logs client with retries."""
        for attempt in range(self.config['max_retries']):
            try:
                self.cloudwatch_logs = boto3.client(
                    'logs',
                    region_name=self.config['aws_region'],
                    aws_access_key_id=self.config['aws_access_key_id'],
                    aws_secret_access_key=self.config['aws_secret_access_key']
                )
                
                # Test connection
                self.cloudwatch_logs.describe_log_groups(limit=1)
                logger.info(f"Successfully connected to AWS CloudWatch Logs in region {self.config['aws_region']}")
                return
                
            except NoCredentialsError:
                logger.error("AWS credentials not found or invalid")
                raise
            except ClientError as e:
                logger.error(f"AWS client error on attempt {attempt + 1}: {e}")
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'])
                else:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error initializing AWS client: {e}")
                raise
    
    def _initialize_kafka_producer(self):
        """Initialize Kafka producer with retries."""
        for attempt in range(self.config['max_retries']):
            try:
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=[self.config['kafka_broker']],
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    retries=3,
                    retry_backoff_ms=1000
                )
                logger.info(f"Successfully connected to Kafka at {self.config['kafka_broker']}")
                return
                
            except NoBrokersAvailable:
                logger.warning(f"Kafka brokers not available. Retrying in {self.config['retry_delay']} seconds... (Attempt {attempt + 1}/{self.config['max_retries']})")
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'])
                else:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error connecting to Kafka: {e}")
                raise
    
    def _load_checkpoints(self):
        """Load checkpoint data from file."""
        try:
            if os.path.exists(self.config['checkpoint_file']):
                with open(self.config['checkpoint_file'], 'rb') as f:
                    self.checkpoints = pickle.load(f)
                logger.info(f"Loaded checkpoints for {len(self.checkpoints)} log groups")
            else:
                # Initialize checkpoints for each log group
                self.checkpoints = {
                    log_group: {
                        'next_token': None,
                        'last_ingestion_time': int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)  # Start from 1 hour ago
                    }
                    for log_group in self.config['log_groups']
                }
                self._save_checkpoints()
                logger.info("Initialized new checkpoints")
        except Exception as e:
            logger.error(f"Error loading checkpoints: {e}")
            # Initialize empty checkpoints
            self.checkpoints = {
                log_group: {
                    'next_token': None,
                    'last_ingestion_time': int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
                }
                for log_group in self.config['log_groups']
            }
    
    def _save_checkpoints(self):
        """Save checkpoint data to file."""
        try:
            os.makedirs(os.path.dirname(self.config['checkpoint_file']), exist_ok=True)
            with open(self.config['checkpoint_file'], 'wb') as f:
                pickle.dump(self.checkpoints, f)
            logger.debug("Checkpoints saved successfully")
        except Exception as e:
            logger.error(f"Error saving checkpoints: {e}")
    
    def _poll_log_group(self, log_group_name):
        """Poll logs from a specific log group."""
        try:
            checkpoint = self.checkpoints.get(log_group_name, {})
            start_time = checkpoint.get('last_ingestion_time')
            next_token = checkpoint.get('next_token')
            
            # Prepare filter_log_events parameters
            params = {
                'logGroupName': log_group_name,
                'startTime': start_time,
                'limit': 100  # Adjust based on your needs
            }
            
            if next_token:
                params['nextToken'] = next_token
            
            response = self.cloudwatch_logs.filter_log_events(**params)
            events = response.get('events', [])
            
            if not events:
                logger.debug(f"No new events found in log group: {log_group_name}")
                return 0
            
            logs_sent = 0
            latest_timestamp = start_time
            
            for event in events:
                # Create structured log message
                log_message = {
                    'source': 'aws-cloudwatch',
                    'host': log_group_name,
                    'timestamp': event['timestamp'],
                    'level': self._extract_log_level(event['message']),
                    'message': event['message'],
                    'log_group': log_group_name,
                    'log_stream': event.get('logStreamName', ''),
                    'event_id': event.get('eventId', ''),
                    'ingestion_time': event.get('ingestionTime', event['timestamp'])
                }
                
                # Send to Kafka
                self.kafka_producer.send(self.config['kafka_topic'], log_message)
                logs_sent += 1
                
                # Update latest timestamp
                if event['timestamp'] > latest_timestamp:
                    latest_timestamp = event['timestamp']
            
            # Update checkpoint
            self.checkpoints[log_group_name] = {
                'next_token': response.get('nextToken'),
                'last_ingestion_time': latest_timestamp + 1  # Add 1ms to avoid duplicate
            }
            
            # Flush producer and save checkpoints
            self.kafka_producer.flush()
            self._save_checkpoints()
            
            logger.info(f"Polled {logs_sent} logs from {log_group_name}")
            return logs_sent
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.warning(f"Log group not found: {log_group_name}")
            elif error_code == 'ThrottlingException':
                logger.warning(f"Throttled while polling {log_group_name}, will retry later")
                time.sleep(10)  # Wait before next attempt
            else:
                logger.error(f"AWS error polling {log_group_name}: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error polling log group {log_group_name}: {e}")
            return 0
    
    def _extract_log_level(self, message):
        """Extract log level from message content."""
        message_upper = message.upper()
        
        if any(keyword in message_upper for keyword in ['ERROR', 'FATAL', 'CRITICAL']):
            return 'ERROR'
        elif any(keyword in message_upper for keyword in ['WARN', 'WARNING']):
            return 'WARNING'
        elif 'DEBUG' in message_upper:
            return 'DEBUG'
        elif any(keyword in message_upper for keyword in ['INFO', 'INFORMATION']):
            return 'INFO'
        else:
            return 'INFO'  # Default to INFO
    
    def run(self):
        """Main polling loop."""
        logger.info(f"Starting AWS Log Poller for log groups: {', '.join(self.config['log_groups'])}")
        logger.info(f"Polling interval: {self.config['poll_interval']} seconds")
        
        try:
            while True:
                start_time = time.time()
                total_logs_processed = 0
                
                for log_group in self.config['log_groups']:
                    try:
                        logs_count = self._poll_log_group(log_group)
                        total_logs_processed += logs_count
                    except Exception as e:
                        logger.error(f"Error processing log group {log_group}: {e}")
                        continue
                
                elapsed_time = time.time() - start_time
                logger.info(f"Polling cycle completed in {elapsed_time:.2f}s, processed {total_logs_processed} logs")
                
                # Sleep for remaining interval time
                sleep_time = max(0, self.config['poll_interval'] - elapsed_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("AWS Log Poller stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up AWS Log Poller...")
        
        if self.kafka_producer:
            try:
                self.kafka_producer.flush()
                self.kafka_producer.close()
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")
        
        # Save final checkpoints
        self._save_checkpoints()
        logger.info("AWS Log Poller shutdown complete")


def main():
    """Main entry point."""
    try:
        poller = AWSLogPoller()
        poller.run()
    except Exception as e:
        logger.error(f"Failed to start AWS Log Poller: {e}")
        exit(1)


if __name__ == "__main__":
    main()
