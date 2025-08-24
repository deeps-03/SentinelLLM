from kafka import KafkaProducer
import json
import time
import random

KAFKA_BROKER = 'kafka:9093'
KAFKA_TOPIC = 'logs'

from kafka.errors import NoBrokersAvailable

producer = None
MAX_RETRIES = 20
RETRY_DELAY_SEC = 10

# Attempt to connect to Kafka with a retry mechanism in case the broker is not yet available.
for i in range(MAX_RETRIES):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(f"Successfully connected to Kafka after {i+1} attempts.")
        break
    except NoBrokersAvailable:
        print(f"Kafka brokers not available. Retrying in {RETRY_DELAY_SEC} seconds... (Attempt {i+1}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY_SEC)
    except Exception as e:
        print(f"An unexpected error occurred during Kafka connection: {e}")
        break

if producer is None:
    print("Failed to connect to Kafka after multiple retries. Exiting.")
    exit(1)

def generate_log():
    log_types = ["INFO", "WARNING", "ERROR", "DEBUG"]
    messages = {
        "INFO": [
            "User logged in successfully.",
            "Data processed for report generation.",
            "System health check passed.",
            "New session started."
        ],
        "WARNING": [
            "Disk space low on /var/log.",
            "High CPU usage detected.",
            "Deprecated API endpoint accessed.",
            "Failed to refresh cache."
        ],
        "ERROR": [
            "Database connection failed.",
            "NullPointerException in main service.",
            "Authentication failed for user 'admin'.",
            "Service 'payment' is unreachable."
        ],
        "DEBUG": [
            "Variable 'x' value: 10.",
            "Entering function 'process_data'.",
            "Received request from IP 192.168.1.1."
        ]
    }
    
    log_type = random.choices(log_types, weights=[0.4, 0.4, 0.15, 0.05], k=1)[0]
    message = random.choice(messages[log_type])
    
    log_entry = {
        "timestamp": time.time(),
        "level": log_type,
        "message": message,
        "service": random.choice(["auth-service", "data-pipeline", "web-app", "api-gateway"])
    }
    return log_entry

if __name__ == "__main__":
    print(f"Starting log producer for topic: {KAFKA_TOPIC}")
    print(f"Connecting to Kafka broker: {KAFKA_BROKER}")
    try:
        while True:
            log = generate_log()
            producer.send(KAFKA_TOPIC, log)
            print(f"Produced: {log}")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\nProducer stopped by user.")
    finally:
        producer.close()
