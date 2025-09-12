import json
from kafka import KafkaConsumer

# --- Kafka Configuration ---
KAFKA_BROKER = 'kafka:9093'
KAFKA_RAW_LOGS_TOPIC = 'raw-logs'
OUTPUT_FILE = 'labeled_logs.jsonl'

# --- Kafka Consumer ---
consumer = KafkaConsumer(
    KAFKA_RAW_LOGS_TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    auto_offset_reset='earliest',
    enable_auto_commit=False,
    group_id='log-labeling-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print(f"Starting log labeling tool for topic: {KAFKA_RAW_LOGS_TOPIC}")
print("Press Ctrl+C to stop.")

try:
    with open(OUTPUT_FILE, 'a') as f:
        for message in consumer:
            log_entry = message.value
            log_message = log_entry.get("message", "")

            print("\n" + "="*50)
            print(f"Log Message: {log_message}")
            print("="*50)

            while True:
                label = input("Enter classification (1: incident, 2: preventive_action, 3: normal, s: skip): ")
                if label in ['1', '2', '3', 's']:
                    break
                else:
                    print("Invalid input. Please enter 1, 2, 3, or s.")

            if label == 's':
                continue

            classification = ""
            if label == '1':
                classification = 'incident'
            elif label == '2':
                classification = 'preventive_action'
            elif label == '3':
                classification = 'normal'

            labeled_data = {
                "text": f"Log Entry: \"{log_message}\"",
                "label": classification
            }

            f.write(json.dumps(labeled_data) + '\n')
            print(f"Saved: {labeled_data}")

except KeyboardInterrupt:
    print("\nLabeling tool stopped by user.")
finally:
    consumer.close()
    print("Log labeling tool shut down.")
