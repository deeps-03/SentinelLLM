#!/usr/bin/env python3

import json
from kafka import KafkaConsumer, KafkaProducer
import time

def test_kafka_connection():
    print("Testing Kafka connection...")
    
    # Test producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            request_timeout_ms=10000,
            api_version=(0, 10, 1)
        )
        
        # Send a test message
        test_message = {"test": "message", "timestamp": time.time()}
        future = producer.send('logs', test_message)
        
        # Wait for message to be sent
        record_metadata = future.get(timeout=10)
        print(f"✓ Successfully sent test message to topic '{record_metadata.topic}' partition {record_metadata.partition}")
        
        producer.close()
        
    except Exception as e:
        print(f"✗ Producer test failed: {e}")
        return False
    
    # Test consumer
    try:
        consumer = KafkaConsumer(
            'logs',
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='latest',
            enable_auto_commit=True,
            group_id='test-group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=5000,
            api_version=(0, 10, 1)
        )
        
        print("✓ Consumer connected successfully")
        print("Listening for messages (5 second timeout)...")
        
        message_count = 0
        for message in consumer:
            print(f"✓ Received: {message.value}")
            message_count += 1
            if message_count >= 3:  # Just get a few messages
                break
                
        consumer.close()
        print(f"✓ Successfully received {message_count} messages")
        
    except Exception as e:
        print(f"✗ Consumer test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if test_kafka_connection():
        print("🎉 Kafka connection test PASSED!")
    else:
        print("❌ Kafka connection test FAILED!")
