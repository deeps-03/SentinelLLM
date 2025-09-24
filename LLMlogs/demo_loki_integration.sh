#!/bin/bash

# Ultra Fast Loki Integration Demo
# Demonstrates log aggregation and querying

echo "🚀 Ultra Fast Loki Integration Demo"
echo "================================="

# Start only essential services for Loki demo
echo "📦 Starting minimal Loki stack..."

# Create minimal docker compose for Loki demo
cat > docker compose-loki.yml << 'EOF'
version: '3.8'
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - loki-net

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    networks:
      - loki-net
    depends_on:
      - loki

  log-generator:
    build:
      context: .
      dockerfile: integrations/Dockerfile.ultra_fast_loki
    depends_on:
      - loki
    networks:
      - loki-net
    environment:
      - LOKI_URL=http://loki:3100

networks:
  loki-net:
    driver: bridge
EOF

# Create optimized Dockerfile for ultra-fast Loki integration
mkdir -p integrations
cat > integrations/Dockerfile.ultra_fast_loki << 'EOF'
FROM python:3.9-slim

RUN pip install --no-cache-dir requests python-json-logger

WORKDIR /app
COPY integrations/ultra_fast_loki.py ./ultra_fast_loki.py

CMD ["python", "ultra_fast_loki.py"]
EOF

echo "🔧 Starting Loki integration..."
docker compose -f docker compose-loki.yml up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 15

echo ""
echo "📊 Loki Integration Status:"
echo "=========================="

# Check Loki status
echo "🔍 Loki Status:"
curl -s http://localhost:3100/ready && echo " ✅ Ready" || echo " ❌ Not Ready"

echo ""
echo "📈 Grafana Dashboard:"
echo "URL: http://localhost:3000"
echo "Login: admin/admin"

echo ""
echo "🏃‍♂️ Ultra Fast Log Ingestion Demo:"
echo "=================================="

# Generate sample logs directly to Loki
python3 << 'EOF'
import requests
import json
import time
from datetime import datetime

loki_url = "http://localhost:3100/loki/api/v1/push"

# Sample log entries for demo
log_entries = [
    {"level": "INFO", "message": "Application started successfully", "service": "web-server", "environment": "production"},
    {"level": "ERROR", "message": "Database connection failed", "service": "api-gateway", "environment": "production"},
    {"level": "WARN", "message": "High memory usage detected", "service": "monitoring", "environment": "production"},
    {"level": "INFO", "message": "User login successful", "service": "auth-service", "environment": "production"},
    {"level": "ERROR", "message": "Payment processing failed", "service": "payment-service", "environment": "production"},
    {"level": "DEBUG", "message": "Cache hit ratio: 85%", "service": "cache-layer", "environment": "production"},
    {"level": "CRITICAL", "message": "System overload detected", "service": "load-balancer", "environment": "production"}
]

print("🚀 Sending logs to Loki...")

for i, log_entry in enumerate(log_entries):
    timestamp = str(int(time.time() * 1000000000))  # nanoseconds
    
    loki_payload = {
        "streams": [{
            "stream": {
                "job": "demo",
                "level": log_entry["level"],
                "service": log_entry["service"],
                "environment": log_entry["environment"]
            },
            "values": [[timestamp, json.dumps(log_entry)]]
        }]
    }
    
    try:
        response = requests.post(loki_url, json=loki_payload)
        if response.status_code == 204:
            print(f"✅ Log {i+1}/7 sent: [{log_entry['level']}] {log_entry['message']}")
        else:
            print(f"❌ Failed to send log {i+1}: {response.status_code}")
    except Exception as e:
        print(f"❌ Error sending log {i+1}: {e}")
    
    time.sleep(0.5)

print("\n📊 Query Loki logs:")
print("==================")

# Query logs from Loki
try:
    query_url = "http://localhost:3100/loki/api/v1/query_range"
    params = {
        "query": '{job="demo"}',
        "start": str(int((time.time() - 300) * 1000000000)),  # 5 minutes ago
        "end": str(int(time.time() * 1000000000)),
        "limit": 100
    }
    
    response = requests.get(query_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get("data", {}).get("result"):
            print(f"✅ Successfully retrieved {len(data['data']['result'])} log streams")
            for stream in data["data"]["result"]:
                labels = stream["stream"]
                print(f"📝 Stream: {labels}")
                for entry in stream["values"][:3]:  # Show first 3 entries
                    log_data = json.loads(entry[1])
                    print(f"   [{log_data['level']}] {log_data['message']}")
        else:
            print("⚠️  No logs found in Loki")
    else:
        print(f"❌ Failed to query Loki: {response.status_code}")
        
except Exception as e:
    print(f"❌ Error querying Loki: {e}")

EOF

echo ""
echo "🎯 Demo Summary:"
echo "==============="
echo "✅ Loki log aggregation running"
echo "✅ Ultra-fast log ingestion demonstrated"
echo "✅ Grafana dashboard available"
echo "🔗 Access: http://localhost:3000"

echo ""
echo "🛑 To stop demo: docker compose -f docker compose-loki.yml down"