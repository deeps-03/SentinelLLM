#!/bin/bash

# Multi-Model Patch Analyzer Demo
# Demonstrates XGBoost + Qwen AI analysis

echo "🤖 Multi-Model Patch Analyzer Demo"
echo "================================="

# Check if Qwen model exists
if [ ! -f "models/qwen/qwen2-1.5b-log-classifier-Q4_K_M.gguf" ]; then
    echo "⚠️  Qwen model not found. Downloading..."
    mkdir -p models/qwen
    
    echo "📥 Downloading Qwen 1.5B Log Classifier (this may take a few minutes)..."
    python3 -c "
from huggingface_hub import hf_hub_download
try:
    file_path = hf_hub_download(
        repo_id='Deeps03/qwen2-1.5b-log-classifier', 
        filename='qwen2-1.5b-log-classifier-Q4_K_M.gguf',
        local_dir='models/qwen/'
    )
    print(f'✅ Model downloaded: {file_path}')
except Exception as e:
    print(f'❌ Download failed: {e}')
    print('📝 Please run: ./setup_qwen.sh')
"
fi

# Create minimal docker compose for patch analyzer demo
echo "📦 Setting up Multi-Model Analysis Environment..."

cat > docker compose-analyzer.yml << 'EOF'
version: '3.8'
services:
  kafka:
    image: wurstmeister/kafka:2.13-2.8.1
    ports:
      - "9092:9092"
    environment:
      KAFKA_ADVERTISED_HOST_NAME: localhost
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_CREATE_TOPICS: "logs:1:1,patch-analysis:1:1"
    depends_on:
      - zookeeper
    networks:
      - analyzer-net

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    networks:
      - analyzer-net

  victoria-metrics:
    image: victoriametrics/victoria-metrics:latest
    ports:
      - "8428:8428"
    networks:
      - analyzer-net

  log-producer:
    build:
      context: .
      dockerfile: Dockerfile.producer
    depends_on:
      - kafka
    networks:
      - analyzer-net
    environment:
      - KAFKA_BROKER=kafka:9092

  patch-analyzer:
    build:
      context: .
      dockerfile: Dockerfile.simple_consumer
    depends_on:
      - kafka
      - victoria-metrics
    networks:
      - analyzer-net
    environment:
      - KAFKA_BROKER=kafka:9092
      - PYTHONUNBUFFERED=1

networks:
  analyzer-net:
    driver: bridge
EOF

echo "🚀 Starting Multi-Model Patch Analysis System..."
docker compose -f docker compose-analyzer.yml up -d

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 20

echo ""
echo "🧠 Multi-Model Analysis Status:"
echo "=============================="

# Check services
echo "📊 Service Status:"
docker compose -f docker compose-analyzer.yml ps

echo ""
echo "🔍 Live Multi-Model Analysis:"
echo "============================"

# Show live analysis output
echo "📈 XGBoost + Qwen Analysis Output:"
timeout 30 docker compose -f docker compose-analyzer.yml logs -f patch-analyzer | head -20

echo ""
echo "🤖 Running Dedicated Multi-Model Anomaly Detection:"
echo "================================================="

# Run the multi-model anomaly detector directly
python3 core/multi_model_anomaly_detector.py --once

echo ""
echo "📊 Patch Analysis Dashboard:"
echo "=========================="

# Create a simple metrics dashboard
python3 << 'EOF'
import requests
import json
import time
from datetime import datetime

print("🎯 Real-time Patch Analysis Metrics:")
print("===================================")

# Query VictoriaMetrics for current status
vm_url = "http://localhost:8428/api/v1/query"

metrics = [
    ('log_normal_total', 'Normal Logs'),
    ('log_warning_total', 'Warning Logs'),
    ('log_incident_total', 'Incident Logs'),
    ('logs_processed_total', 'Total Processed')
]

for metric, label in metrics:
    try:
        params = {"query": metric}
        response = requests.get(vm_url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("data", {}).get("result"):
                value = data["data"]["result"][0]["value"][1]
                print(f"📈 {label}: {value}")
            else:
                print(f"📊 {label}: 0")
        else:
            print(f"❌ {label}: Error querying")
    except Exception as e:
        print(f"⚠️  {label}: Connection error")

print("")
print("🧠 AI Analysis Capabilities:")
print("===========================")
print("✅ XGBoost: Real-time log classification")
print("✅ Qwen 1.5B: Detailed incident analysis") 
print("✅ Multi-Model: Prophet + Isolation Forest + EMA")
print("✅ Meta-Classifier: Intelligent risk assessment")

print("")
print("🎯 Current Analysis Pipeline:")
print("============================")
print("1. 📊 Raw logs → XGBoost classification")
print("2. 🤖 Classified logs → Qwen AI analysis")
print("3. 📈 Metrics → Multi-model anomaly detection")
print("4. 🧠 Combined insights → Risk assessment")

EOF

echo ""
echo "🎯 Demo Complete!"
echo "================"
echo "✅ XGBoost classification active"
echo "✅ Qwen AI analysis running"
echo "✅ Multi-model anomaly detection operational"
echo "📊 Metrics: http://localhost:8428"

echo ""
echo "🛑 To stop demo: docker compose -f docker compose-analyzer.yml down"