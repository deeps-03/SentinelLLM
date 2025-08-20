import os
import json
import time
import requests
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
KAFKA_BROKER = 'kafka:9093'
KAFKA_TOPIC = 'logs'
KAFKA_RAW_LOGS_TOPIC = os.getenv('RAW_LOGS_TOPIC', 'raw-logs')
KAFKA_CLASSIFIED_LOGS_TOPIC = os.getenv('CLASSIFIED_LOGS_TOPIC', 'classified-logs')
VICTORIAMETRICS_URL = 'http://victoria-metrics:8428/api/v1/import/prometheus'
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MAX_RETRIES = 10
RETRY_DELAY_SEC = 5
METRIC_PUSH_INTERVAL_SEC = 10

# --- Gemini AI Setup ---
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found. Make sure it's set in the .env file.")
    exit(1)

try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Gemini Pro model initialized successfully.")
except Exception as e:
    print(f"Error initializing Gemini Pro model: {e}")
    exit(1)

# --- Kafka Connection ---
consumer = None
producer = None

for i in range(MAX_RETRIES):
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            KAFKA_RAW_LOGS_TOPIC,  # Also consume from raw-logs topic
            bootstrap_servers=[KAFKA_BROKER],
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='log-classifier-group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
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

if consumer is None or producer is None:
    print("Failed to connect to Kafka after multiple retries. Exiting.")
    exit(1)

# --- Metrics & Classification ---
incident_total = 0
warning_total = 0

def push_metrics_to_victoria_metrics():
    """Pushes the current log classification counts to VictoriaMetrics."""
    global incident_total, warning_total
    metrics = [
        f'log_incident_total{{source="log_consumer"}} {incident_total}',
        f'log_warning_total{{source="log_consumer"}} {warning_total}'
    ]
    payload = "\n".join(metrics)
    headers = {'Content-Type': 'text/plain'}
    try:
        response = requests.post(VICTORIAMETRICS_URL, data=payload, headers=headers)
        response.raise_for_status()
        print(f"Pushed metrics to VictoriaMetrics. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error pushing metrics to VictoriaMetrics: {e}")

def classify_log_with_gemini(log_message):
    """
    Classifies a log message using the Gemini Pro API.
    """
    if not log_message:
        return "unknown"
    try:
        # Craft a specific prompt for the classification task
        prompt = f"""
        Analyze the following log entry and classify it into one of three categories: 'incident', 'preventive_action', or 'normal'.
        - 'incident': Indicates a critical error, failure, or security breach that requires immediate attention.
        - 'preventive_action': Indicates a warning or potential issue that should be investigated to prevent future problems.
        - 'normal': Indicates a routine, informational message.

        Log Entry: "{log_message}"

        Classification:
        """
        response = model.generate_content(prompt)
        # Extract the classification from the response text
        classification = response.text.strip().lower()
        if "incident" in classification:
            return "incident"
        if "preventive_action" in classification:
            return "preventive_action"
        return "normal"
    except Exception as e:
        print(f"Error classifying log with Gemini: {e}")
        return "error"

# --- Main Loop ---
if __name__ == "__main__":
    print(f"Starting log consumer for topics: {KAFKA_TOPIC}, {KAFKA_RAW_LOGS_TOPIC}")
    last_metric_push_time = time.time()

    try:
        for message in consumer:
            log_entry = message.value
            log_message = log_entry.get("message", "")

            prediction = classify_log_with_gemini(log_message)
            print(f"Consumed: {{'message': '{log_message[:100]}...'}} -> Classified as: {prediction}")

            # Create classified log entry
            classified_log = {
                **log_entry,  # Include original log data
                'classification': prediction,
                'classified_timestamp': time.time(),
                'source_topic': message.topic
            }
            
            # Send classified log to classified-logs topic
            producer.send(KAFKA_CLASSIFIED_LOGS_TOPIC, classified_log)

            if prediction == "incident":
                incident_total += 1
            elif prediction == "preventive_action":
                warning_total += 1

            current_time = time.time()
            if current_time - last_metric_push_time >= METRIC_PUSH_INTERVAL_SEC:
                push_metrics_to_victoria_metrics()
                last_metric_push_time = current_time

            # Add a 5-second delay to respect the API rate limit
            time.sleep(5)

    except KeyboardInterrupt:
        print("\nConsumer stopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if consumer:
            consumer.close()
        if producer:
            producer.flush()
            producer.close()
        # Push final metrics before exiting
        push_metrics_to_victoria_metrics()
        print("Log consumer shut down.")
