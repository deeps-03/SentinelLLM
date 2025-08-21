"""
Azure Monitor / Log Analytics Poller Service

This service connects to Azure Monitor / Log Analytics workspace, queries logs
in near real-time, and pushes them into Kafka topic 'raw-logs'. It maintains
checkpoints to avoid duplicating logs after restarts.
"""

import os
import json
import time
from azure.monitor.query import LogsQueryClient
from azure.identity import ClientSecretCredential
from azure.core.exceptions import HttpResponseError
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta, timezone
import pickle
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AzureLogPoller:
    """Azure Monitor / Log Analytics polling service with checkpoint management."""
    
    def __init__(self):
        self.config = {
            'kafka_broker': os.getenv('KAFKA_BROKER', 'kafka:9093'),
            'kafka_topic': os.getenv('RAW_LOGS_TOPIC', 'raw-logs'),
            'azure_tenant_id': os.getenv('AZURE_TENANT_ID'),
            'azure_client_id': os.getenv('AZURE_CLIENT_ID'),
            'azure_client_secret': os.getenv('AZURE_CLIENT_SECRET'),
            'azure_workspace_id': os.getenv('AZURE_WORKSPACE_ID'),
            'azure_query': os.getenv('AZURE_QUERY', 'union * | where TimeGenerated > ago(1h) | order by TimeGenerated desc | limit 100'),
            'poll_interval': int(os.getenv('AZURE_POLL_INTERVAL_SECONDS', '60')),
            'checkpoint_file': '/app/checkpoints/azure_checkpoint.pkl',
            'max_retries': int(os.getenv('MAX_RETRIES', '5')),
            'retry_delay': int(os.getenv('RETRY_DELAY_SECONDS', '5'))
        }
        
        # Validate configuration
        self._validate_config()
        
        # Initialize clients
        self.logs_client = None
        self.kafka_producer = None
        self.checkpoint = {}
        
        # Initialize services
        self._initialize_azure_client()
        self._initialize_kafka_producer()
        self._load_checkpoint()
    
    def _validate_config(self):
        """Validate required configuration parameters."""
        required_vars = [
            'azure_tenant_id', 'azure_client_id', 'azure_client_secret',
            'azure_workspace_id'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not self.config.get(var):
                missing_vars.append(var.upper())
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def _initialize_azure_client(self):
        """Initialize Azure Monitor Logs client with retries."""
        for attempt in range(self.config['max_retries']):
            try:
                # Create credential
                credential = ClientSecretCredential(
                    tenant_id=self.config['azure_tenant_id'],
                    client_id=self.config['azure_client_id'],
                    client_secret=self.config['azure_client_secret']
                )
                
                # Create logs client
                self.logs_client = LogsQueryClient(credential)
                
                # Test connection with a simple query
                test_query = "union * | limit 1"
                self.logs_client.query_workspace(
                    workspace_id=self.config['azure_workspace_id'],
                    query=test_query,
                    timespan=timedelta(hours=1)
                )
                
                logger.info(f"Successfully connected to Azure Log Analytics workspace: {self.config['azure_workspace_id']}")
                return
                
            except Exception as e:
                logger.error(f"Azure client error on attempt {attempt + 1}: {e}")
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'])
                else:
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
    
    def _load_checkpoint(self):
        """Load checkpoint data from file."""
        try:
            if os.path.exists(self.config['checkpoint_file']):
                with open(self.config['checkpoint_file'], 'rb') as f:
                    self.checkpoint = pickle.load(f)
                logger.info("Loaded checkpoint data")
            else:
                # Initialize checkpoint - start from 1 hour ago
                self.checkpoint = {
                    'last_query_time': datetime.now(timezone.utc) - timedelta(hours=1)
                }
                self._save_checkpoint()
                logger.info("Initialized new checkpoint")
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            # Initialize empty checkpoint
            self.checkpoint = {
                'last_query_time': datetime.now(timezone.utc) - timedelta(hours=1)
            }
    
    def _save_checkpoint(self):
        """Save checkpoint data to file."""
        try:
            os.makedirs(os.path.dirname(self.config['checkpoint_file']), exist_ok=True)
            with open(self.config['checkpoint_file'], 'wb') as f:
                pickle.dump(self.checkpoint, f)
            logger.debug("Checkpoint saved successfully")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    def _build_query(self):
        """Build KQL query with time filter based on checkpoint."""
        base_query = self.config['azure_query']
        last_time = self.checkpoint.get('last_query_time')
        
        if last_time:
            # Convert to KQL datetime format
            time_filter = f"TimeGenerated > datetime({last_time.isoformat()})"
            
            # If the base query already contains a time filter, replace it
            if 'TimeGenerated >' in base_query:
                # Replace existing time filter
                base_query = re.sub(
                    r'TimeGenerated\s*>\s*[^|]+',
                    time_filter,
                    base_query
                )
            else:
                # Add time filter
                # Find the first pipe and insert the filter before it
                if '|' in base_query:
                    parts = base_query.split('|', 1)
                    base_query = f"{parts[0].strip()} | where {time_filter} | {parts[1].strip()}"
                else:
                    base_query = f"{base_query} | where {time_filter}"
        
        return base_query
    
    def _poll_azure_logs(self):
        """Poll logs from Azure Monitor."""
        try:
            query = self._build_query()
            logger.debug(f"Executing query: {query}")
            
            # Query with appropriate timespan
            current_time = datetime.now(timezone.utc)
            timespan = current_time - self.checkpoint.get('last_query_time', current_time - timedelta(hours=1))
            
            response = self.logs_client.query_workspace(
                workspace_id=self.config['azure_workspace_id'],
                query=query,
                timespan=timespan
            )
            
            if not response.tables:
                logger.debug("No data returned from Azure query")
                return 0
            
            logs_sent = 0
            latest_timestamp = self.checkpoint.get('last_query_time', current_time - timedelta(hours=1))
            
            # Process each table in the response
            for table in response.tables:
                # Get column names
                column_names = [col.name for col in table.columns]
                
                for row in table.rows:
                    # Create a dictionary from row data
                    row_dict = dict(zip(column_names, row))
                    
                    # Extract timestamp - common column names
                    timestamp = None
                    for ts_col in ['TimeGenerated', 'Timestamp', 'EventTime', '_TimeGenerated']:
                        if ts_col in row_dict:
                            timestamp = row_dict[ts_col]
                            break
                    
                    if timestamp:
                        # Ensure timestamp is timezone-aware
                        if isinstance(timestamp, str):
                            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        elif hasattr(timestamp, 'replace') and timestamp.tzinfo is None:
                            timestamp = timestamp.replace(tzinfo=timezone.utc)
                        
                        # Update latest timestamp
                        if timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                    else:
                        timestamp = current_time
                    
                    # Create structured log message
                    log_message = {
                        'source': 'azure-monitor',
                        'host': row_dict.get('Computer', row_dict.get('_ResourceId', 'unknown')),
                        'timestamp': int(timestamp.timestamp() * 1000),  # Convert to milliseconds
                        'level': self._extract_log_level(row_dict),
                        'message': self._extract_message(row_dict),
                        'workspace_id': self.config['azure_workspace_id'],
                        'table_name': table.name if hasattr(table, 'name') else 'unknown',
                        'raw_data': row_dict
                    }
                    
                    # Send to Kafka
                    self.kafka_producer.send(self.config['kafka_topic'], log_message)
                    logs_sent += 1
            
            # Update checkpoint
            self.checkpoint['last_query_time'] = latest_timestamp
            
            # Flush producer and save checkpoint
            self.kafka_producer.flush()
            self._save_checkpoint()
            
            logger.info(f"Polled {logs_sent} logs from Azure Monitor")
            return logs_sent
            
        except HttpResponseError as e:
            if e.status_code == 429:  # Rate limited
                logger.warning("Azure API rate limited, will retry later")
                time.sleep(60)  # Wait 1 minute
            else:
                logger.error(f"Azure HTTP error: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error polling Azure logs: {e}")
            return 0
    
    def _extract_log_level(self, row_dict):
        """Extract log level from row data."""
        # Check common level column names
        for level_col in ['Level', 'SeverityLevel', 'LogLevel', 'EventLevel', 'Category']:
            if level_col in row_dict and row_dict[level_col]:
                level_value = str(row_dict[level_col]).upper()
                
                # Map numeric severity levels (common in Azure)
                level_mapping = {
                    '0': 'VERBOSE', '1': 'INFO', '2': 'WARNING', 
                    '3': 'ERROR', '4': 'CRITICAL'
                }
                
                if level_value in level_mapping:
                    return level_mapping[level_value]
                
                # Direct text mapping
                if any(keyword in level_value for keyword in ['ERROR', 'FATAL', 'CRITICAL']):
                    return 'ERROR'
                elif any(keyword in level_value for keyword in ['WARN', 'WARNING']):
                    return 'WARNING'
                elif 'DEBUG' in level_value or 'VERBOSE' in level_value:
                    return 'DEBUG'
                elif any(keyword in level_value for keyword in ['INFO', 'INFORMATION']):
                    return 'INFO'
        
        # Fallback: check message content
        message = self._extract_message(row_dict).upper()
        if any(keyword in message for keyword in ['ERROR', 'FATAL', 'CRITICAL']):
            return 'ERROR'
        elif any(keyword in message for keyword in ['WARN', 'WARNING']):
            return 'WARNING'
        elif 'DEBUG' in message:
            return 'DEBUG'
        else:
            return 'INFO'  # Default to INFO
    
    def _extract_message(self, row_dict):
        """Extract message content from row data."""
        # Check common message column names
        for msg_col in ['Message', 'RenderedDescription', 'Description', 'EventData', 'RawEventData']:
            if msg_col in row_dict and row_dict[msg_col]:
                return str(row_dict[msg_col])
        
        # Fallback: concatenate all string values
        message_parts = []
        for key, value in row_dict.items():
            if isinstance(value, str) and value.strip() and key not in ['TimeGenerated', 'Timestamp', '_TimeGenerated']:
                message_parts.append(f"{key}: {value}")
        
        return " | ".join(message_parts) if message_parts else "No message content"
    
    def run(self):
        """Main polling loop."""
        logger.info(f"Starting Azure Log Poller for workspace: {self.config['azure_workspace_id']}")
        logger.info(f"Polling interval: {self.config['poll_interval']} seconds")
        logger.info(f"Query: {self.config['azure_query']}")
        
        try:
            while True:
                start_time = time.time()
                
                try:
                    logs_processed = self._poll_azure_logs()
                except Exception as e:
                    logger.error(f"Error in polling cycle: {e}")
                    logs_processed = 0
                
                elapsed_time = time.time() - start_time
                logger.info(f"Polling cycle completed in {elapsed_time:.2f}s, processed {logs_processed} logs")
                
                # Sleep for remaining interval time
                sleep_time = max(0, self.config['poll_interval'] - elapsed_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("Azure Log Poller stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up Azure Log Poller...")
        
        if self.kafka_producer:
            try:
                self.kafka_producer.flush()
                self.kafka_producer.close()
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")
        
        # Save final checkpoint
        self._save_checkpoint()
        logger.info("Azure Log Poller shutdown complete")


def main():
    """Main entry point."""
    try:
        poller = AzureLogPoller()
        poller.run()
    except Exception as e:
        logger.error(f"Failed to start Azure Log Poller: {e}")
        exit(1)


if __name__ == "__main__":
    main()
