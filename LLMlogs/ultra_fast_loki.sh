#!/bin/bash

# Ultra Fast Loki Integration with Real Log Generation
echo "🚀 Ultra Fast Loki + Real Log Data Generation"
echo "=============================================="

# Start minimal Loki stack
echo "📦 Starting Loki services..."
cat > docker compose-ultra-loki.yml << 'EOF'
version: '3.8'
services:
  loki:
    image: grafana/loki:2.9.0
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
    volumes:
      - ./grafana-loki-performance-dashboard.json:/etc/grafana/provisioning/dashboards/dashboard.json
    networks:
      - loki-net

  log-generator:
    build:
      context: .
      dockerfile: Dockerfile.ultra_fast_loki
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

# Create the ultra-fast log generator
cat > integrations/ultra_fast_loki.py << 'EOF'
#!/usr/bin/env python3
"""
Ultra Fast Loki Log Generator with Realistic Spike Patterns
Generates logs with time-based patterns, spikes, and anomalies
"""

import requests
import json
import time
import random
import math
from datetime import datetime, timedelta
import threading
from typing import List, Dict

class LogSpikePatternsGenerator:
    def __init__(self, loki_url="http://loki:3100"):
        self.loki_url = loki_url
        self.push_url = f"{loki_url}/loki/api/v1/push"
        self.running = True
        
        # Spike patterns for different scenarios
        self.spike_patterns = {
            "normal_operation": {"base_rate": 10, "spike_probability": 0.02, "spike_intensity": 2},
            "patch_deployment": {"base_rate": 20, "spike_probability": 0.15, "spike_intensity": 8},
            "system_stress": {"base_rate": 50, "spike_probability": 0.25, "spike_intensity": 15},
            "recovery_phase": {"base_rate": 15, "spike_probability": 0.08, "spike_intensity": 4}
        }
        
        # Log types with different error rates
        self.log_types = {
            "application": {"normal_error_rate": 0.05, "spike_error_rate": 0.3},
            "system": {"normal_error_rate": 0.02, "spike_error_rate": 0.2},
            "network": {"normal_error_rate": 0.08, "spike_error_rate": 0.4},
            "database": {"normal_error_rate": 0.03, "spike_error_rate": 0.25}
        }

    def generate_realistic_log_entry(self, log_type: str, is_spike: bool, timestamp: datetime) -> Dict:
        """Generate a realistic log entry with appropriate patterns"""
        
        error_rate = self.log_types[log_type]["spike_error_rate" if is_spike else "normal_error_rate"]
        is_error = random.random() < error_rate
        
        if log_type == "application":
            if is_error:
                messages = [
                    "Database connection timeout after 30s",
                    "Memory allocation failed for request buffer", 
                    "Authentication service unavailable",
                    "API rate limit exceeded for user session",
                    "Cache invalidation failed for key: user_data_*"
                ]
                level = "ERROR"
                classification = "incident"
            else:
                messages = [
                    "User authentication successful",
                    "Request processed successfully in 45ms",
                    "Cache hit for user preferences",
                    "API response sent with 200 status",
                    "Session updated for user activity"
                ]
                level = "INFO"
                classification = "normal"
                
        elif log_type == "system":
            if is_error:
                messages = [
                    "CPU usage above 90% for 5 consecutive minutes",
                    "Disk space critically low: 95% full",
                    "Memory usage warning: 85% utilized",
                    "Network interface eth0 packet loss detected",
                    "File system read-only due to I/O errors"
                ]
                level = "CRITICAL"
                classification = "incident"
            else:
                messages = [
                    "System health check passed",
                    "Scheduled backup completed successfully",
                    "Service restart completed",
                    "System monitoring active",
                    "Resource utilization within normal bounds"
                ]
                level = "INFO"
                classification = "normal"
                
        elif log_type == "network":
            if is_error:
                messages = [
                    "TCP connection reset by peer",
                    "DNS resolution failed for external service",
                    "SSL handshake timeout",
                    "Load balancer health check failed",
                    "Firewall blocked suspicious traffic"
                ]
                level = "WARNING"
                classification = "preventive_action"
            else:
                messages = [
                    "HTTP request completed successfully",
                    "SSL certificate validation passed", 
                    "Load balancer routing healthy",
                    "Network latency within SLA",
                    "CDN cache serving requests efficiently"
                ]
                level = "INFO"
                classification = "normal"
                
        elif log_type == "database":
            if is_error:
                messages = [
                    "Query execution timeout: SELECT * FROM large_table",
                    "Connection pool exhausted",
                    "Deadlock detected in transaction",
                    "Index rebuild required for performance",
                    "Replication lag exceeding threshold"
                ]
                level = "ERROR"
                classification = "incident"
            else:
                messages = [
                    "Database query executed in 12ms",
                    "Transaction committed successfully",
                    "Index usage optimized for query",
                    "Connection pool status healthy",
                    "Replication synchronization complete"
                ]
                level = "INFO"
                classification = "normal"
        
        # Add spike-specific intensity markers
        if is_spike:
            message = f"[SPIKE-{random.randint(1000,9999)}] {random.choice(messages)}"
        else:
            message = random.choice(messages)
            
        return {
            "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": level,
            "log_type": log_type,
            "message": message,
            "classification": classification,
            "spike": is_spike,
            "response_time_ms": random.randint(10, 500) if not is_spike else random.randint(200, 2000),
            "memory_usage_mb": random.randint(100, 512) if not is_spike else random.randint(400, 1024)
        }

    def send_logs_to_loki(self, logs: List[Dict]):
        """Send batch of logs to Loki"""
        
        # Group logs by labels for Loki streams
        streams = {}
        
        for log in logs:
            # Create stream key based on log characteristics  
            stream_key = f'{log["log_type"]}_{log["level"].lower()}'
            
            if stream_key not in streams:
                streams[stream_key] = {
                    "stream": {
                        "job": "ultra_fast_log_generator",
                        "log_type": log["log_type"],
                        "level": log["level"],
                        "classification": log["classification"]
                    },
                    "values": []
                }
            
            # Convert to Loki format: [timestamp_ns, log_line]
            timestamp_ns = str(int(datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00')).timestamp() * 1_000_000_000))
            log_line = json.dumps(log)
            
            streams[stream_key]["values"].append([timestamp_ns, log_line])
        
        # Send to Loki
        payload = {"streams": list(streams.values())}
        
        try:
            response = requests.post(
                self.push_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=5
            )
            
            if response.status_code == 204:
                print(f"✅ Sent {len(logs)} logs to Loki")
            else:
                print(f"⚠️  Loki response: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Failed to send logs to Loki: {e}")

    def simulate_scenario(self, scenario: str, duration_minutes: int):
        """Simulate a specific scenario with realistic patterns"""
        
        print(f"🎬 Simulating scenario: {scenario.upper()} for {duration_minutes} minutes")
        
        pattern = self.spike_patterns[scenario]
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        scenario_logs = []
        
        while datetime.now() < end_time and self.running:
            current_time = datetime.now()
            
            # Generate logs based on pattern
            logs_this_batch = []
            
            for _ in range(pattern["base_rate"]):
                log_type = random.choice(list(self.log_types.keys()))
                
                # Determine if this should be a spike
                is_spike = random.random() < pattern["spike_probability"]
                
                if is_spike:
                    # Generate multiple logs for spike intensity
                    for _ in range(pattern["spike_intensity"]):
                        log_entry = self.generate_realistic_log_entry(log_type, True, current_time)
                        logs_this_batch.append(log_entry)
                        scenario_logs.append(log_entry)
                else:
                    log_entry = self.generate_realistic_log_entry(log_type, False, current_time)
                    logs_this_batch.append(log_entry)
                    scenario_logs.append(log_entry)
            
            # Send batch to Loki
            if logs_this_batch:
                self.send_logs_to_loki(logs_this_batch)
            
            # Wait before next batch
            time.sleep(2)
        
        print(f"✅ Scenario {scenario} completed. Generated {len(scenario_logs)} logs")
        return scenario_logs

    def run_continuous_generation(self):
        """Run continuous log generation with varying patterns"""
        
        print("🚀 Starting continuous ultra-fast log generation")
        print("📊 Simulating realistic system patterns:")
        
        scenarios = [
            ("normal_operation", 2),    # 2 minutes normal
            ("patch_deployment", 3),    # 3 minutes patch stress  
            ("system_stress", 2),       # 2 minutes high load
            ("recovery_phase", 2),      # 2 minutes recovery
        ]
        
        try:
            while self.running:
                for scenario, duration in scenarios:
                    if not self.running:
                        break
                    self.simulate_scenario(scenario, duration)
                    
                    if self.running:
                        print("⏱️  Waiting 30 seconds before next scenario...")
                        time.sleep(30)
                        
        except KeyboardInterrupt:
            print("\n🛑 Stopping log generation...")
            self.running = False

def main():
    print("🎯 Ultra Fast Loki Log Generator")
    print("=" * 40)
    
    generator = LogSpikePatternsGenerator()
    
    # Wait for Loki to be ready
    print("⏳ Waiting for Loki to be ready...")
    max_retries = 30
    
    for i in range(max_retries):
        try:
            response = requests.get(f"{generator.loki_url}/ready", timeout=2)
            if response.status_code == 200:
                print("✅ Loki is ready!")
                break
        except:
            pass
        
        print(f"⏳ Waiting for Loki... ({i+1}/{max_retries})")
        time.sleep(2)
    else:
        print("❌ Loki not ready, but continuing anyway...")
    
    # Start generating logs
    generator.run_continuous_generation()

if __name__ == "__main__":
    main()
EOF

# Create Dockerfile for ultra fast log generator
cat > Dockerfile.ultra_fast_loki << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install required packages
COPY requirements_simple.txt .
RUN pip install --no-cache-dir -r requirements_simple.txt

# Copy the ultra fast generator
COPY integrations/ultra_fast_loki.py .

CMD ["python", "ultra_fast_loki.py"]
EOF

echo "🚀 Starting ultra fast Loki stack..."
docker compose -f docker compose-ultra-loki.yml up -d

echo ""
echo "✅ Ultra Fast Loki Integration Started!"
echo "📊 Services running:"
echo "   • Loki: http://localhost:3100"
echo "   • Grafana: http://localhost:3000 (admin/admin)"
echo "   • Log Generator: Producing realistic spike patterns"
echo ""
echo "🎬 Generating realistic log patterns:"
echo "   • Normal operation (low spike rate)"
echo "   • Patch deployment (high error rate)"
echo "   • System stress (frequent spikes)"  
echo "   • Recovery phase (moderate activity)"
echo ""
echo "💡 View logs in Grafana or query Loki directly"
echo "🛑 Press Ctrl+C to stop or run: docker compose -f docker compose-ultra-loki.yml down"

# Keep running until interrupted
trap 'echo "🛑 Stopping ultra fast Loki..."; docker compose -f docker compose-ultra-loki.yml down; exit 0' INT
echo "⏳ Ultra fast Loki running... Press Ctrl+C to stop"
while true; do
    sleep 10
    echo "📈 Log generation active - $(date)"
done