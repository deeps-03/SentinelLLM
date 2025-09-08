#!/usr/bin/env python3
"""
Load Testing Script for Loki + Kafka Integration
Tests system behavior under high-volume log bursts (10,000+ events)
"""

import asyncio
import aiohttp
import json
import time
import random
import string
from typing import List, Dict
from datetime import datetime, timezone
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LokiLoadTester:
    def __init__(self, loki_url: str, concurrent_clients: int = 50, events_per_second: int = 10000):
        self.loki_url = loki_url.rstrip('/')
        self.concurrent_clients = concurrent_clients
        self.events_per_second = events_per_second
        self.session = None
        
        # Test data templates
        self.log_templates = [
            "ERROR: Database connection failed for user {user_id} at {timestamp}",
            "INFO: User {user_id} successfully logged in from IP {ip_address}",
            "WARNING: High memory usage detected: {memory_usage}% on server {server_id}",
            "CRITICAL: Security breach attempt from IP {ip_address} targeting {endpoint}",
            "DEBUG: Processing batch job {job_id} with {record_count} records",
            "INFO: API request to {endpoint} completed in {response_time}ms",
            "ERROR: Payment processing failed for transaction {transaction_id}",
            "WARNING: Disk space low on server {server_id}: {disk_usage}% used",
            "INFO: Background task {task_id} completed successfully",
            "CRITICAL: Service {service_name} is down, failover initiated"
        ]
        
        self.sources = ["web-server", "api-gateway", "database", "payment-service", "auth-service", "worker-nodes"]
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def generate_log_entry(self) -> Dict:
        """Generate a realistic log entry"""
        template = random.choice(self.log_templates)
        source = random.choice(self.sources)
        
        # Generate random data for placeholders
        log_data = {
            'user_id': f"user_{random.randint(1000, 9999)}",
            'ip_address': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            'memory_usage': random.randint(60, 95),
            'server_id': f"srv-{random.randint(100, 999)}",
            'endpoint': random.choice(['/api/users', '/api/payments', '/api/orders', '/health', '/metrics']),
            'job_id': f"job_{random.randint(10000, 99999)}",
            'record_count': random.randint(100, 10000),
            'response_time': random.randint(50, 2000),
            'transaction_id': f"txn_{random.randint(100000, 999999)}",
            'disk_usage': random.randint(80, 95),
            'task_id': f"task_{random.randint(1000, 9999)}",
            'service_name': random.choice(['auth-svc', 'payment-svc', 'order-svc', 'notification-svc']),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Format the log message
        try:
            message = template.format(**log_data)
        except KeyError:
            message = template
            
        # Create Loki log entry
        return {
            "stream": {
                "source": source,
                "level": self.extract_log_level(message),
                "service": f"sentinellm-{source}",
                "environment": "production"
            },
            "values": [
                [str(int(time.time() * 1000000000)), message]  # nanosecond timestamp
            ]
        }
    
    def extract_log_level(self, message: str) -> str:
        """Extract log level from message"""
        if message.startswith("ERROR"):
            return "error"
        elif message.startswith("WARNING"):
            return "warning"
        elif message.startswith("CRITICAL"):
            return "critical"
        elif message.startswith("DEBUG"):
            return "debug"
        else:
            return "info"
    
    async def send_batch_to_loki(self, logs: List[Dict]) -> Dict:
        """Send a batch of logs to Loki"""
        payload = {"streams": logs}
        
        try:
            async with self.session.post(
                f"{self.loki_url}/loki/api/v1/push",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                return {
                    'status': response.status,
                    'success': response.status == 204,
                    'batch_size': len(logs),
                    'timestamp': time.time()
                }
        except Exception as e:
            logger.error(f"Failed to send batch to Loki: {e}")
            return {
                'status': 0,
                'success': False,
                'batch_size': len(logs),
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def client_worker(self, client_id: int, logs_per_client: int, batch_size: int = 100) -> List[Dict]:
        """Worker function for each client"""
        results = []
        logs_sent = 0
        
        logger.info(f"Client {client_id} starting - target: {logs_per_client} logs")
        
        while logs_sent < logs_per_client:
            # Create batch
            batch = []
            batch_target = min(batch_size, logs_per_client - logs_sent)
            
            for _ in range(batch_target):
                batch.append(self.generate_log_entry())
            
            # Send batch
            result = await self.send_batch_to_loki(batch)
            result['client_id'] = client_id
            results.append(result)
            
            logs_sent += batch_target
            
            # Small delay to control rate
            await asyncio.sleep(0.1)
        
        logger.info(f"Client {client_id} completed - sent {logs_sent} logs")
        return results
    
    async def run_load_test(self, duration_seconds: int = 300, batch_size: int = 100) -> Dict:
        """Run the load test"""
        start_time = time.time()
        total_logs_target = self.events_per_second * duration_seconds
        logs_per_client = total_logs_target // self.concurrent_clients
        
        logger.info(f"Starting load test:")
        logger.info(f"  Target rate: {self.events_per_second} events/sec")
        logger.info(f"  Duration: {duration_seconds} seconds")
        logger.info(f"  Concurrent clients: {self.concurrent_clients}")
        logger.info(f"  Total logs target: {total_logs_target}")
        logger.info(f"  Logs per client: {logs_per_client}")
        logger.info(f"  Batch size: {batch_size}")
        
        # Start all client workers
        tasks = []
        for client_id in range(self.concurrent_clients):
            task = asyncio.create_task(
                self.client_worker(client_id, logs_per_client, batch_size)
            )
            tasks.append(task)
        
        # Wait for all clients to complete
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Aggregate results
        successful_batches = 0
        failed_batches = 0
        total_logs_sent = 0
        errors = []
        
        for client_results in all_results:
            if isinstance(client_results, Exception):
                errors.append(str(client_results))
                continue
                
            for result in client_results:
                if result['success']:
                    successful_batches += 1
                    total_logs_sent += result['batch_size']
                else:
                    failed_batches += 1
                    if 'error' in result:
                        errors.append(result['error'])
        
        actual_rate = total_logs_sent / actual_duration if actual_duration > 0 else 0
        
        test_results = {
            'test_config': {
                'target_rate': self.events_per_second,
                'duration_seconds': duration_seconds,
                'concurrent_clients': self.concurrent_clients,
                'batch_size': batch_size
            },
            'results': {
                'actual_duration': actual_duration,
                'total_logs_sent': total_logs_sent,
                'actual_rate': actual_rate,
                'successful_batches': successful_batches,
                'failed_batches': failed_batches,
                'error_rate': failed_batches / (successful_batches + failed_batches) if (successful_batches + failed_batches) > 0 else 0,
                'errors': errors[:10]  # First 10 errors
            }
        }
        
        return test_results

class KafkaLoadTester:
    """Test Kafka consumption after Loki processing"""
    
    def __init__(self, kafka_bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = kafka_bootstrap_servers
        
    async def test_kafka_consumption(self, duration_seconds: int = 60) -> Dict:
        """Test Kafka message consumption rates"""
        try:
            from kafka import KafkaConsumer
            import threading
            
            # Track consumption metrics
            metrics = {
                'raw_logs_consumed': 0,
                'classified_logs_consumed': 0,
                'start_time': time.time(),
                'errors': []
            }
            
            def consume_topic(topic: str, metric_key: str):
                try:
                    consumer = KafkaConsumer(
                        topic,
                        bootstrap_servers=[self.bootstrap_servers],
                        group_id=f'load_test_{topic}_{int(time.time())}',
                        auto_offset_reset='latest',
                        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
                    )
                    
                    start_time = time.time()
                    while time.time() - start_time < duration_seconds:
                        messages = consumer.poll(timeout_ms=1000)
                        for tp, msgs in messages.items():
                            metrics[metric_key] += len(msgs)
                            
                    consumer.close()
                except Exception as e:
                    metrics['errors'].append(f"{topic}: {str(e)}")
            
            # Start consumers for both topics
            threads = []
            for topic, metric_key in [('raw-logs', 'raw_logs_consumed'), ('classified-logs', 'classified_logs_consumed')]:
                thread = threading.Thread(target=consume_topic, args=(topic, metric_key))
                thread.start()
                threads.append(thread)
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            actual_duration = time.time() - metrics['start_time']
            
            return {
                'kafka_test_results': {
                    'duration': actual_duration,
                    'raw_logs_rate': metrics['raw_logs_consumed'] / actual_duration,
                    'classified_logs_rate': metrics['classified_logs_consumed'] / actual_duration,
                    'total_consumed': metrics['raw_logs_consumed'] + metrics['classified_logs_consumed'],
                    'errors': metrics['errors']
                }
            }
            
        except ImportError:
            return {'kafka_test_results': {'error': 'kafka-python not installed'}}
        except Exception as e:
            return {'kafka_test_results': {'error': str(e)}}

async def main():
    parser = argparse.ArgumentParser(description='Load test Loki + Kafka integration')
    parser.add_argument('--loki-url', default='http://localhost:3100', help='Loki URL')
    parser.add_argument('--kafka-servers', default='localhost:9092', help='Kafka bootstrap servers')
    parser.add_argument('--rate', type=int, default=10000, help='Target events per second')
    parser.add_argument('--duration', type=int, default=300, help='Test duration in seconds')
    parser.add_argument('--clients', type=int, default=50, help='Concurrent clients')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for Loki pushes')
    parser.add_argument('--output', help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    logger.info("Starting Loki + Kafka load testing...")
    
    # Test Loki ingestion
    async with LokiLoadTester(args.loki_url, args.clients, args.rate) as loki_tester:
        loki_results = await loki_tester.run_load_test(args.duration, args.batch_size)
    
    # Test Kafka consumption
    kafka_tester = KafkaLoadTester(args.kafka_servers)
    kafka_results = await kafka_tester.test_kafka_consumption(60)
    
    # Combine results
    final_results = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'loki_test': loki_results,
        **kafka_results
    }
    
    # Print summary
    print("\n" + "="*60)
    print("LOAD TEST RESULTS SUMMARY")
    print("="*60)
    print(f"Target Rate: {args.rate:,} events/sec")
    print(f"Actual Rate: {loki_results['results']['actual_rate']:,.1f} events/sec")
    print(f"Total Logs Sent: {loki_results['results']['total_logs_sent']:,}")
    print(f"Success Rate: {(1 - loki_results['results']['error_rate'])*100:.1f}%")
    print(f"Test Duration: {loki_results['results']['actual_duration']:.1f}s")
    
    if 'kafka_test_results' in kafka_results and 'error' not in kafka_results['kafka_test_results']:
        kafka_res = kafka_results['kafka_test_results']
        print(f"Kafka Raw Logs Rate: {kafka_res['raw_logs_rate']:,.1f} msgs/sec")
        print(f"Kafka Classified Rate: {kafka_res['classified_logs_rate']:,.1f} msgs/sec")
    
    print("="*60)
    
    # Save detailed results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(final_results, f, indent=2)
        print(f"Detailed results saved to: {args.output}")

if __name__ == "__main__":
    asyncio.run(main())