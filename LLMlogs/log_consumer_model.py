import os
import json
import time
import pickle
import requests
import traceback
from collections import OrderedDict
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
from dotenv import load_dotenv
from langchain_community.llms import LlamaCpp
import xgboost as xgb
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder

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

# --- Load XGBoost Model ---
MAX_MODEL_LOAD_RETRIES = 10
RETRY_DELAY_SEC = 5

for i in range(MAX_MODEL_LOAD_RETRIES):
    try:
        with open('vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)
        with open('label_encoder.pkl', 'rb') as f:
            label_encoder = pickle.load(f)
        with open('xgboost_model.pkl', 'rb') as f:
            xgb_model = pickle.load(f)
        print("XGBoost model, vectorizer, and label encoder loaded successfully.")
        break  # Exit loop if successful
    except FileNotFoundError:
        print("Error: Model files not found. Make sure to train the model first.")
        exit(1)
    except Exception as e:
        print(f"Error loading XGBoost model: {e}. Retrying in {RETRY_DELAY_SEC} seconds... (Attempt {i+1}/{MAX_MODEL_LOAD_RETRIES})")
        if i == MAX_MODEL_LOAD_RETRIES - 1:
            print("Failed to load model after multiple retries. Exiting.")
            exit(1)
        time.sleep(RETRY_DELAY_SEC)

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

# --- Function to get suggestions from Qwen ---
def get_warning_suggestions(log_message):
    if not llm_model:
        print("Error: Qwen model not available.")
        return None

    if not log_message:
        return None

    try:
        prompt = f"""<|im_start|>system
You are a helpful assistant that analyzes log messages and provides actionable suggestions.
<|im_end|>
<|im_start|>user
Analyze the following warning log and provide suggestions on how to fix it.
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

            # Classify the log using XGBoost
            vectorized_log = vectorizer.transform([log_message])
            prediction_encoded = xgb_model.predict(vectorized_log)[0]
            prediction = label_encoder.inverse_transform([prediction_encoded])[0]

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
