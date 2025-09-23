#!/usr/bin/python3

import time
import random
import requests
from datetime import datetime

# Configuration
VICTORIAMETRICS_URL = 'http://localhost:8428/api/v1/import/prometheus'
INTERVAL_SECONDS = 5

# Simulate realistic log patterns
def generate_metrics():
    """Generate realistic SentinelLLM metrics"""
    current_time = int(time.time() * 1000)
    
    # Base rates (logs per minute)
    base_incidents = random.randint(0, 3)
    base_warnings = random.randint(2, 8) 
    base_info = random.randint(15, 40)
    
    # Add some business hour patterns
    hour = datetime.now().hour
    if 9 <= hour <= 17:  # Business hours
        multiplier = 1.5
    else:
        multiplier = 0.7
        
    incidents = int(base_incidents * multiplier)
    warnings = int(base_warnings * multiplier)
    info_logs = int(base_info * multiplier)
    
    # Occasionally simulate patch deployment spikes
    if random.random() < 0.1:  # 10% chance of deployment spike
        incidents += random.randint(5, 15)
        warnings += random.randint(10, 25)
        print("🚨 Simulating deployment spike!")
    
    total_logs = incidents + warnings + info_logs
    
    # Create metrics in Prometheus format
    metrics = [
        f'log_incident_total {incidents} {current_time}',
        f'log_warning_total {warnings} {current_time}',
        f'log_info_total {info_logs} {current_time}',
        f'logs_processed_total {total_logs} {current_time}',
        f'log_classification_confidence_avg {random.uniform(0.7, 0.95):.3f} {current_time}',
        f'log_processing_rate_per_minute {total_logs} {current_time}',
        f'system_memory_usage_percent {random.uniform(45, 85):.1f} {current_time}',
        f'system_cpu_usage_percent {random.uniform(20, 70):.1f} {current_time}',
        f'kafka_messages_per_second {random.uniform(5, 25):.1f} {current_time}',
        f'anomaly_detection_alerts_total {incidents} {current_time}',
    ]
    
    return '\n'.join(metrics)

def send_metrics():
    """Send metrics to VictoriaMetrics"""
    try:
        metrics_data = generate_metrics()
        
        response = requests.post(
            VICTORIAMETRICS_URL,
            data=metrics_data,
            headers={'Content-Type': 'text/plain'},
            timeout=5
        )
        
        if response.status_code == 204:
            incidents = len([line for line in metrics_data.split('\n') if 'log_incident_total' in line])
            print(f"✅ Metrics sent successfully - {datetime.now().strftime('%H:%M:%S')}")
        else:
            print(f"❌ Failed to send metrics: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error sending metrics: {e}")

def main():
    print("📊 SentinelLLM Metrics Generator Started")
    print("=" * 50)
    print(f"🎯 Target: {VICTORIAMETRICS_URL}")
    print(f"⏰ Interval: {INTERVAL_SECONDS} seconds")
    print(f"📈 Dashboard: http://localhost:3000/d/97421c11-7a01-414e-b607-3c701c9cc21f/")
    print("=" * 50)
    
    try:
        while True:
            send_metrics()
            time.sleep(INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("\n🛑 Metrics generator stopped")

if __name__ == "__main__":
    main()