# --- Imports ---
import os  # For accessing environment variables
import json  # For parsing Kafka messages (JSON format)
import time  # For delays, retries, and metric intervals
import requests  # For sending HTTP requests (VictoriaMetrics + Local model API)
from collections import OrderedDict

# --- Caching Configuration ---
log_cache = OrderedDict()
CACHE_SIZE = 100
from kafka import KafkaConsumer  # Kafka client for consuming messages
from kafka.errors import NoBrokersAvailable  # Error handling when Kafka broker unavailable
import google.generativeai as genai  # Google Gemini API client
from dotenv import load_dotenv  # Load environment variables from .env file

# --- Load environment variables from .env file ---
load_dotenv()

# --- Configuration ---
KAFKA_BROKER = 'kafka:9093'  # Kafka broker host:port
KAFKA_TOPIC = 'logs'  # Kafka topic to consume logs from
VICTORIAMETRICS_URL = 'http://victoria-metrics:8428/api/v1/import/prometheus'  # VictoriaMetrics endpoint
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Gemini API key from environment
OLLAMA_API_URL = "http://ollama:11434/api/generate"  # Ollama API endpoint

MAX_RETRIES = 10  # Max retries for Kafka connection
RETRY_DELAY_SEC = 5  # Retry delay (seconds)
METRIC_PUSH_INTERVAL_SEC = 10  # Interval for pushing metrics to VictoriaMetrics

# --- Gemini AI Setup ---
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found. Make sure it's set in the .env file.")
    exit(1)

try:
    genai.configure(api_key=GEMINI_API_KEY)  # Configure Gemini with API key
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')  # Load Gemini model
    print("Gemini Pro model initialized successfully.")
except Exception as e:
    print(f"Error initializing Gemini Pro model: {e}")
    gemini_model = None  # Fallback if initialization fails

# --- Kafka Connection ---
consumer = None
for i in range(MAX_RETRIES):
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,  # Kafka topic
            bootstrap_servers=[KAFKA_BROKER],  # Kafka broker address
            auto_offset_reset='earliest',  # Start from earliest messages if no offset
            enable_auto_commit=True,  # Automatically commit offsets
            group_id='log-classifier-group',  # Consumer group name
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))  # Deserialize JSON
        )
        print(f"Successfully connected to Kafka after {i+1} attempts.")
        break
    except NoBrokersAvailable:
        print(f"Kafka brokers not available. Retrying in {RETRY_DELAY_SEC} seconds... (Attempt {i+1}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY_SEC)
    except Exception as e:
        print(f"An unexpected error occurred during Kafka connection: {e}")
        break

if consumer is None:
    print("Failed to connect to Kafka after multiple retries. Exiting.")
    exit(1)

# --- Metrics & Classification counters ---
incident_total = 0  # Count of incident logs
warning_total = 0  # Count of preventive_action logs


# --- Function to push metrics to VictoriaMetrics ---
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


# --- Function to classify logs using Gemini ---
def classify_log_with_gemini(log_message):
    """Classifies a log message using the Gemini Pro API. Returns the classification (str) or None if an error occurs."""
    if not gemini_model:
        print("Error: Gemini model not available.")
        return None

    if not log_message:
        return "unknown"

    try:
        prompt = f"""
        Analyze the following log entry and classify it into one of three categories: 'incident', 'preventive_action', or 'normal'.
        - 'incident': Indicates a critical error, failure, or security breach that requires immediate attention.
        - 'preventive_action': Indicates a warning or potential issue that should be investigated to prevent future problems.
        - 'normal': Indicates a routine, informational message.
        Log Entry: "{log_message}"
        Classification:
        """
        response = gemini_model.generate_content(prompt)
        classification = response.text.strip().lower()

        if "incident" in classification:
            return "incident"
        if "preventive_action" in classification:
            return "preventive_action"
        return "normal"

    except Exception as e:
        print(f"Error classifying log with Gemini: {e}")
        return None


# --- Function to classify logs using Local Model ---
def classify_log_with_local_model(log_message, api_url):
    """Classifies a log message using a local model. Returns (classification, confidence)."""
    if not log_message:
        return "unknown", 0

    # Check cache first
    if log_message in log_cache:
        # Move to end to mark as recently used (LRU)
        log_cache.move_to_end(log_message)
        return log_cache[log_message]

    try:
        prompt = f"""
        Analyze the following log entry and classify it into one of three categories: 'incident', 'preventive_action', or 'normal'.
        After the classification, on a new line, provide a confidence score from 1 (very uncertain) to 10 (very certain).
        Log Entry: "{log_message}"
        Classification:
        Confidence:
        """
        headers = {"Content-Type": "application/json"}
        data = {"prompt": prompt, "model": "ollama", "stream": False}

        response = requests.post(api_url, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        response_json = response.json()
        content = ""
        if api_url == OLLAMA_API_URL:
            content = response_json.get('response', '').strip().lower()

        classification = "unknown"
        confidence = 0

        lines = content.split('\n')
        for line in lines:
            if line.lower().startswith("classification:"):
                classification = line.split(":")[1].strip()
            elif line.lower().startswith("confidence:"):
                try:
                    confidence = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass

        # Store in cache
        result = (classification, confidence)
        log_cache[log_message] = result
        if len(log_cache) > CACHE_SIZE:
            log_cache.popitem(last=False) # Remove oldest item (first in order)

        return classification, confidence

    except requests.exceptions.ConnectionError:
        print(f"Error: API not reachable at {api_url}. Is it running?")
        return None, 0
    except requests.exceptions.RequestException as e:
        print(f"Error classifying log with local model: {e}")
        return None, 0
    except Exception as e:
        print(f"Unexpected error in local model classification: {e}")
        return None, 0


# --- Main Execution ---
if __name__ == "__main__":
    print(f"Starting log consumer for topic: {KAFKA_TOPIC}")
    last_metric_push_time = time.time()

    try:
        for message in consumer:
            log_entry = message.value
            log_message = log_entry.get("message", "")

            # Step 1: Try Ollama
            final_prediction, confidence = classify_log_with_local_model(log_message, OLLAMA_API_URL)

            # Step 2: If Ollama fails, fall back to Gemini
            if final_prediction is None or final_prediction == "unknown":
                print("Ollama failed or returned unknown. Falling back to Gemini API...")
                final_prediction = classify_log_with_gemini(log_message)
                confidence = 0

            # Step 3: If all models fail, mark as unknown
            if final_prediction is None:
                print("All models failed. Marking as 'unknown'.")
                final_prediction = "unknown"

            # Print result
            print(f"Consumed: {{'message': '{log_message[:100]}...'}} -> Classified as: {final_prediction} (Confidence: {confidence})\n")

            # Step 5: Update counters
            if final_prediction == "incident":
                incident_total += 1
            elif final_prediction == "preventive_action":
                warning_total += 1

            # Step 6: Push metrics periodically
            current_time = time.time()
            if current_time - last_metric_push_time >= METRIC_PUSH_INTERVAL_SEC:
                push_metrics_to_victoria_metrics()
                last_metric_push_time = current_time

            time.sleep(1)  # Avoid hammering services

    except KeyboardInterrupt:
        print("\nConsumer stopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if consumer:
            consumer.close()
        push_metrics_to_victoria_metrics()
        print("Log consumer shut down.")

# --- End of Script ---
