import os
import json
import time
import pickle
import requests
import traceback
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
from dotenv import load_dotenv
import xgboost as xgb
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder

# Try to import LLM dependencies
try:
    from langchain_community.llms import LlamaCpp
    LLM_AVAILABLE = True
    print("🤖 LLM dependencies available - Qwen suggestions enabled!")
except ImportError:
    LLM_AVAILABLE = False
    print("⚠️  LLM dependencies not available - using basic suggestions")

# Load environment variables
load_dotenv()

# Configuration
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:9093')
KAFKA_TOPIC = 'logs'
KAFKA_RAW_LOGS_TOPIC = os.getenv('RAW_LOGS_TOPIC', 'raw-logs')
KAFKA_CLASSIFIED_LOGS_TOPIC = os.getenv('CLASSIFIED_LOGS_TOPIC', 'classified-logs')
VICTORIAMETRICS_URL = 'http://victoria-metrics:8428/api/v1/import/prometheus'

print(f"🔧 Using Kafka broker: {KAFKA_BROKER}")
print(f"🔧 Using VictoriaMetrics URL: {VICTORIAMETRICS_URL}")

MAX_RETRIES = 10
RETRY_DELAY_SEC = 5

print("Loading XGBoost model...")

# Load XGBoost Model
try:
    with open('vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)
    with open('label_encoder.pkl', 'rb') as f:
        label_encoder = pickle.load(f)
    with open('xgboost_model.pkl', 'rb') as f:
        xgb_model = pickle.load(f)
    print("✓ XGBoost model, vectorizer, and label encoder loaded successfully.")
except FileNotFoundError as e:
    print(f"✗ Error: {e}. Make sure model files exist.")
    exit(1)

# Initialize Qwen LLM if available
llm_model = None
if LLM_AVAILABLE:
    model_path = "./qwen2-1.5b-log-classifier-Q4_K_M.gguf"
    try:
        print(f"🤖 Loading Qwen model '{model_path}'...")
        llm_model = LlamaCpp(
            model_path=model_path,
            n_ctx=2048,
            n_gpu_layers=0,
            n_batch=512,
            verbose=False,
        )
        print(f"✅ Qwen LLM model '{model_path}' initialized successfully!")
    except Exception as e:
        print(f"⚠️  Error initializing Qwen model '{model_path}': {e}")
        print("⚠️  Continuing with basic suggestions...")
        llm_model = None

print("Connecting to Kafka...")

# Kafka Connection
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
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            api_version=(0, 10, 1),
            request_timeout_ms=30000,
            session_timeout_ms=10000
        )
        
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version=(0, 10, 1),
            request_timeout_ms=30000
        )
        
        print(f"✓ Successfully connected to Kafka after {i+1} attempts.")
        break
    except NoBrokersAvailable:
        print(f"⚠ Kafka brokers not available. Retrying in {RETRY_DELAY_SEC} seconds... (Attempt {i+1}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY_SEC)
    except Exception as e:
        print(f"✗ An unexpected error occurred during Kafka connection: {e}")
        break

if consumer is None or producer is None:
    print("✗ Failed to connect to Kafka after multiple retries. Exiting.")
    exit(1)

# Metrics counters
incident_total = 0
warning_total = 0
normal_total = 0

def push_metrics_to_victoria_metrics():
    global incident_total, warning_total, normal_total

    metrics = [
        f'log_incident_total{{source="simple_consumer"}} {incident_total}',
        f'log_warning_total{{source="simple_consumer"}} {warning_total}',
        f'log_normal_total{{source="simple_consumer"}} {normal_total}'
    ]
    payload = "\n".join(metrics)
    headers = {'Content-Type': 'text/plain'}

    try:
        response = requests.post(VICTORIAMETRICS_URL, data=payload, headers=headers)
        response.raise_for_status()
        print(f"✓ Pushed metrics to VictoriaMetrics. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠ Error pushing metrics to VictoriaMetrics: {e}")

def get_warning_suggestions(log_message):
    """Get AI-powered suggestions for warning/preventive action logs"""
    if not llm_model:
        return f"Review and address: {log_message[:100]}..."
    
    if not log_message:
        return None
    
    try:
        prompt = f"""<|im_start|>system
You are an expert DevOps engineer and system administrator. Analyze log messages and provide detailed, actionable solutions to fix issues. Your responses should include:
1. Root cause analysis
2. Immediate fix steps
3. Prevention measures
4. Commands/scripts when applicable
<|im_end|>
<|im_start|>user
Analyze this warning log and provide detailed steps to fix it:

Log: "{log_message}"

Please provide:
1. What the issue is
2. Immediate fix steps with specific commands
3. Long-term prevention measures
4. Monitoring recommendations
<|im_end|>
<|im_start|>assistant
"""
        
        generated_text = llm_model.invoke(prompt).strip()
        return generated_text
    
    except Exception as e:
        print(f"⚠️  Error getting suggestions from Qwen: {e}")
        return f"Basic suggestion: Review and address: {log_message[:100]}..."

def get_incident_solutions(log_message):
    """Get AI-powered emergency solutions for incident logs"""
    if not llm_model:
        return f"URGENT: Investigate immediately: {log_message[:100]}..."
    
    if not log_message:
        return None
    
    try:
        prompt = f"""<|im_start|>system
You are an expert incident response engineer. Analyze critical system failures and provide IMMEDIATE emergency response steps. Focus on:
1. Emergency containment actions
2. Quick diagnostic commands
3. Immediate recovery steps
4. Escalation procedures
<|im_end|>
<|im_start|>user
CRITICAL INCIDENT - Provide immediate emergency response for:

Log: "{log_message}"

Provide urgent steps:
1. IMMEDIATE actions to contain the issue
2. Diagnostic commands to run NOW
3. Quick recovery procedures
4. When to escalate
<|im_end|>
<|im_start|>assistant
"""
        
        generated_text = llm_model.invoke(prompt).strip()
        return generated_text
    
    except Exception as e:
        print(f"⚠️  Error getting incident solutions from Qwen: {e}")
        return f"URGENT: Investigate immediately: {log_message[:100]}..."

if __name__ == "__main__":
    print(f"🚀 Starting simple log consumer for topics: {KAFKA_TOPIC}, {KAFKA_RAW_LOGS_TOPIC}")
    print("=" * 60)
    
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
            
            # Get AI-powered solutions based on classification
            if prediction == 'preventive_action':
                print(f"🧠 Getting AI suggestions for: {log_message[:50]}...")
                suggestions = get_warning_suggestions(log_message)
                if suggestions:
                    classified_log['suggestions'] = suggestions
                    print(f"💡 AI DETAILED SOLUTION:")
                    print("=" * 80)
                    print(suggestions)
                    print("=" * 80)
            elif prediction == 'incident':
                print(f"🚨 Getting EMERGENCY response for: {log_message[:50]}...")
                solutions = get_incident_solutions(log_message)
                if solutions:
                    classified_log['emergency_response'] = solutions
                    print(f"🚑 EMERGENCY RESPONSE PLAN:")
                    print("🔥" * 40)
                    print(solutions)
                    print("🔥" * 40)
            
            # Send to classified logs topic
            producer.send(KAFKA_CLASSIFIED_LOGS_TOPIC, classified_log)
            
            # Update counters
            if prediction == "incident":
                incident_total += 1
                print(f"🚨 INCIDENT: {log_message[:80]}...")
            elif prediction == "preventive_action":
                warning_total += 1
                print(f"⚠️  WARNING: {log_message[:80]}...")
            else:
                normal_total += 1
                print(f"ℹ️  NORMAL: {log_message[:80]}...")
                
            print(f"   → Classified as: {prediction}")
            print("-" * 60)
            
            # Push metrics every 10 messages
            if (incident_total + warning_total + normal_total) % 10 == 0:
                push_metrics_to_victoria_metrics()
                
    except KeyboardInterrupt:
        print("\n🛑 Consumer stopped by user.")
    except Exception as e:
        print(f"✗ An unexpected error occurred: {e}")
    finally:
        if consumer:
            consumer.close()
        if producer:
            producer.flush()
            producer.close()
        push_metrics_to_victoria_metrics()
        print("✓ Simple log consumer shut down.")
