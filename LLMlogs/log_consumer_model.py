import os
import json
import time
import requests
import traceback
from collections import OrderedDict
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
from dotenv import load_dotenv
from langchain_community.llms import LlamaCpp


# --- Caching Configuration ---
log_cache = OrderedDict()
CACHE_SIZE = 100

# --- Load environment variables from .env file ---
load_dotenv()

# --- Configuration ---
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:9093')
KAFKA_TOPIC = 'logs'
KAFKA_RAW_LOGS_TOPIC = os.getenv('RAW_LOGS_TOPIC', 'raw-logs')
KAFKA_CLASSIFIED_LOGS_TOPIC = os.getenv('CLASSIFIED_LOGS_TOPIC', 'classified-logs')
VICTORIAMETRICS_URL = 'http://victoria-metrics:8428/api/v1/import/prometheus'

MAX_RETRIES = 20
RETRY_DELAY_SEC = 10
METRIC_PUSH_INTERVAL_SEC = 10


# --- Qwen AI (LlamaCpp) Model Setup ---
llm_model = None
model_path = "./qwen-model.gguf"

try:
    llm_model = LlamaCpp(
        model_path=model_path,
        n_ctx=2048,
        n_gpu_layers=0,
        n_batch=512,
        verbose=False,
    )
    print(f"LlamaCpp model '{model_path}' initialized successfully.")
except Exception as e:
    print(f"Error initializing LlamaCpp model '{model_path}': {e}")
    llm_model = None

# --- Kafka Connection ---
consumer = None
producer = None

for i in range(MAX_RETRIES):
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            KAFKA_RAW_LOGS_TOPIC,
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

# --- Metrics & Classification counters ---
incident_total = 0
warning_total = 0

# --- Function to push metrics to VictoriaMetrics ---
def push_metrics_to_victoria_metrics():
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

# --- Function to classify log with Qwen ---
def classify_log_with_llm(log_message):
    if not llm_model:
        print("Error: Qwen model not available.")
        return "normal" # Default classification

    if not log_message:
        return "normal"

    try:
        prompt = f"""<|im_start|>system
You are an expert log analysis assistant. Your task is to classify log messages into one of the following categories: 'incident', 'preventive_action', or 'normal'.
- 'incident': Indicates a critical error, failure, or a significant security breach that requires immediate attention. These are issues that have already caused a service disruption or a security event. Examples: "database connection failed", "service unavailable", "unauthorized access detected", "application crash".
- 'preventive_action': Indicates a warning, a potential issue, or a performance concern that should be addressed to prevent future problems. These are issues that have not yet caused a service disruption, but could lead to one if not addressed. Examples: "low disk space", "high CPU usage", "rate limit approaching", "cache refresh failed", "high latency warning".
- 'normal': Indicates a routine operational message. Examples: "user session started", "data processing complete", "system health check passed", "EC2 instance started".

Provide only the classification category as a single word: 'incident', 'preventive_action', or 'normal'. Do not add any extra characters or quotes.

Example 1:
User: Classify the following log message:
Log Entry: "WARNING: High memory usage on server-db-01"
Assistant: preventive_action

Example 2:
User: Classify the following log message:
Log Entry: "ERROR: Database connection timed out"
Assistant: incident
<|im_end|>
<|im_start|>user
Classify the following log message:
Log Entry: "{log_message}" 
<|im_end|>
<|im_start|>assistant
"""
        
        classification = llm_model.invoke(prompt).strip().lower().strip("'\"")
        
        # Ensure the output is one of the valid classifications
        if classification not in ['incident', 'preventive_action', 'normal']:
            # Here we could add some logic to handle unexpected output from the LLM.
            # For now, we'll default to 'normal' if the output is not what we expect.
            print(f"LLM returned an unexpected classification: '{classification}'. Defaulting to 'normal'.")
            return "normal"
            
        return classification

    except Exception as e:
        print(f"Error getting classification from Qwen: {e}")
        traceback.print_exc()
        return "normal" # Default classification on error


# --- Function to get suggestions from Qwen ---
def get_warning_suggestions(log_message):
    if not llm_model:
        print("Error: Qwen model not available.")
        return None

    if not log_message:
        return None

    try:
        prompt = f"""<|im_start|>system
You are an expert technical assistant trained in log analysis. Your task is to carefully examine log messages, identify errors, anomalies, or performance concerns, and provide precise, actionable recommendations to resolve issues and improve system reliability.
<|im_end|>
<|im_start|>user
Analyze the following warning log and provide technical suggestions on how to fix it.
Log Entry: \"{log_message}\" 
<|im_end|>
<|im_start|>assistant
"""
        
        generated_text = llm_model.invoke(prompt).strip()
        return generated_text

    except Exception as e:
        print(f"Error getting suggestions from Qwen: {e}")
        traceback.print_exc()
        return None

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Starting log consumer for topics: {KAFKA_TOPIC}, {KAFKA_RAW_LOGS_TOPIC}")
    last_metric_push_time = time.time()

    try:
        for message in consumer:
            log_entry = message.value
            log_message = log_entry.get("message", "")

            # Classify the log using the LLM
            prediction = classify_log_with_llm(log_message)

            classified_log = {
                **log_entry,
                'classification': prediction,
                'classified_timestamp': time.time(),
                'source_topic': message.topic
            }

            if prediction == 'preventive_action':
                suggestions = get_warning_suggestions(log_message)
                if suggestions:
                    classified_log['suggestions'] = suggestions
                    print(f"Suggestion for '{log_message[:50]}...': {suggestions}")

            producer.send(KAFKA_CLASSIFIED_LOGS_TOPIC, classified_log)

            print(f"Consumed: {{'message': '{log_message[:100]}...'}} -> Classified as: {prediction}")

            if prediction == "incident":
                incident_total += 1
            elif prediction == "preventive_action":
                warning_total += 1

            current_time = time.time()
            if current_time - last_metric_push_time >= METRIC_PUSH_INTERVAL_SEC:
                push_metrics_to_victoria_metrics()
                last_metric_push_time = current_time

            time.sleep(1)

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
        push_metrics_to_victoria_metrics()
        print("Log consumer shut down.")
