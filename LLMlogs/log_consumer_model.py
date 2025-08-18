# --- Imports ---
import os                     # For accessing environment variables
import json                   # For parsing Kafka messages (JSON format)
import time                   # For delays, retries, and metric intervals
import requests               # For sending HTTP requests (VictoriaMetrics + Local model API)
from kafka import KafkaConsumer          # Kafka client for consuming messages
from kafka.errors import NoBrokersAvailable  # Error handling when Kafka broker unavailable
import google.generativeai as genai      # Google Gemini API client
from dotenv import load_dotenv           # Load environment variables from .env file


# --- Load environment variables from .env file ---
load_dotenv()


# --- Configuration ---
KAFKA_BROKER = 'kafka:9093'   # Kafka broker host:port
KAFKA_TOPIC = 'logs'          # Kafka topic to consume logs from
VICTORIAMETRICS_URL = 'http://victoria-metrics:8428/api/v1/import/prometheus'  # VictoriaMetrics endpoint
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Gemini API key from environment
LOCAL_MODEL_API_URL = "http://gemma3-wrapper:8000/generate"  # Local model API endpoint
MAX_RETRIES = 10              # Max retries for Kafka connection
RETRY_DELAY_SEC = 5           # Retry delay (seconds)
METRIC_PUSH_INTERVAL_SEC = 10 # Interval for pushing metrics to VictoriaMetrics
LOCAL_MODEL_CONFIDENCE_THRESHOLD = 7  # (Unused) threshold for local model confidence


# --- Gemini AI Setup ---
if not GEMINI_API_KEY:  # Check if API key is available
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
for i in range(MAX_RETRIES):  # Try multiple times to connect to Kafka
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,                          # Kafka topic
            bootstrap_servers=[KAFKA_BROKER],     # Kafka broker address
            auto_offset_reset='earliest',         # Start from earliest messages if no offset
            enable_auto_commit=True,              # Automatically commit offsets
            group_id='log-classifier-group',      # Consumer group name
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))  # Deserialize JSON
        )
        print(f"Successfully connected to Kafka after {i+1} attempts.")
        break
    except NoBrokersAvailable:  # Kafka broker unavailable
        print(f"Kafka brokers not available. Retrying in {RETRY_DELAY_SEC} seconds... (Attempt {i+1}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY_SEC)
    except Exception as e:  # Any other error
        print(f"An unexpected error occurred during Kafka connection: {e}")
        break

if consumer is None:  # Exit if connection failed after retries
    print("Failed to connect to Kafka after multiple retries. Exiting.")
    exit(1)


# --- Metrics & Classification counters ---
incident_total = 0   # Count of incident logs
warning_total = 0    # Count of preventive_action logs


# --- Function to push metrics to VictoriaMetrics ---
def push_metrics_to_victoria_metrics():
    """Pushes the current log classification counts to VictoriaMetrics."""
    global incident_total, warning_total
    metrics = [
        f'log_incident_total{{source="log_consumer"}} {incident_total}',  # Metric for incidents
        f'log_warning_total{{source="log_consumer"}} {warning_total}'     # Metric for warnings
    ]
    payload = "\n".join(metrics)  # Format payload in Prometheus format
    headers = {'Content-Type': 'text/plain'}
    try:
        response = requests.post(VICTORIAMETRICS_URL, data=payload, headers=headers)  # Push metrics
        response.raise_for_status()
        print(f"Pushed metrics to VictoriaMetrics. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error pushing metrics to VictoriaMetrics: {e}")


# --- Function to classify logs using Gemini ---
def classify_log_with_gemini(log_message):
    """
    Classifies a log message using the Gemini Pro API.
    Returns the classification (str) or None if an error occurs.
    """
    if not gemini_model:
        print("Error: Gemini model not available.")
        return None
    if not log_message:
        return "unknown"
    try:
        # Prompt for Gemini classification
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
def classify_log_with_local_model(log_message):
    """
    Classifies a log message using the local Docker model (gemma3-qat).
    Returns (classification, confidence) or (None, 0) if an error occurs.
    """
    if not log_message:
        return "unknown", 0
    try:
        # Prompt for local model
        prompt = f"""
        Analyze the following log entry and classify it into one of three categories: 'incident', 'preventive_action', or 'normal'.
        After the classification, on a new line, provide a confidence score from 1 (very uncertain) to 10 (very certain) for your classification.

        Log Entry: "{log_message}"

        Classification:
        Confidence:
        """
        headers = {"Content-Type": "application/json"}
        data = {"prompt": prompt}

        # Send prompt to local API
        response = requests.post(LOCAL_MODEL_API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()

        # Extract JSON response
        response_json = response.json()
        if 'error' in response_json:
            print(f"Local model API returned an error: {response_json['error']}")
            return None, 0
        
        content = response_json.get('choices', [{}])[0].get('message', {}).get('content', '').strip().lower()

        classification = "unknown"
        confidence = 0

        # Parse classification
        if "classification:" in content:
            class_line = content.split("classification:")[1].split("\n")[0].strip()
            if "incident" in class_line:
                classification = "incident"
            elif "preventive_action" in class_line:
                classification = "preventive_action"
            else:
                classification = "normal"

        # Parse confidence score
        if "confidence:" in content:
            try:
                conf_line = content.split("confidence:")[1].split("\n")[0].strip()
                confidence = int(conf_line)
            except (ValueError, IndexError):
                pass

        return classification, confidence

    # --- Error Handling ---
    except requests.exceptions.ConnectionError:
        print(f"Error: Local model API not reachable at {LOCAL_MODEL_API_URL}. Is it running?")
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
    last_metric_push_time = time.time()  # Track last metric push time

    try:
        # Consume messages from Kafka continuously
        for message in consumer:
            log_entry = message.value   # Get Kafka message
            log_message = log_entry.get("message", "")  # Extract "message" field

            # Step 1: Try Gemma (local model) first
            final_prediction, confidence = classify_log_with_local_model(log_message)

            # Step 2: If Gemma fails, fall back to Gemini
            if final_prediction is None:
                print("Local model failed. Falling back to Gemini API...")
                final_prediction = classify_log_with_gemini(log_message)
                confidence = 0  # Gemini doesn't provide a confidence score

            # Step 3: If both models fail, mark as unknown
            if final_prediction is None:
                print("Both local and Gemini models failed. Marking as 'unknown'.")
                final_prediction = "unknown"

            # Print result
            print(f"Consumed: {{'message': '{log_message[:100]}...'}} -> Classified as: {final_prediction} (Confidence: {confidence})\n")

            # Step 4: Update counters
            if final_prediction == "incident":
                incident_total += 1
            elif final_prediction == "preventive_action":
                warning_total += 1

            # Step 5: Push metrics every interval
            current_time = time.time()
            if current_time - last_metric_push_time >= METRIC_PUSH_INTERVAL_SEC:
                push_metrics_to_victoria_metrics()
                last_metric_push_time = current_time

            time.sleep(1)  # Small delay to avoid overloading services

    except KeyboardInterrupt:
        print("\nConsumer stopped by user.")  # Graceful exit
    except Exception as e:
        print(f"An unexpected error occurred: {e}")  # Catch unexpected errors
    finally:
        if consumer:
            consumer.close()  # Close Kafka consumer
        push_metrics_to_victoria_metrics()  # Push final metrics before shutdown
        print("Log consumer shut down.")


# --- End of Script ---