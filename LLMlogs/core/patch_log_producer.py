#!/usr/bin/env python3
"""
Patch Log Producer - Generates realistic patch deployment logs
"""

import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

def generate_patch_log():
    """Generate a realistic patch deployment log"""
    
    scenarios = ["normal", "warning", "error", "critical"]
    scenario = random.choices(scenarios, weights=[0.6, 0.2, 0.15, 0.05])[0]
    
    if scenario == "normal":
        messages = [
            "Patch deployment step 1/5 completed successfully",
            "Service health check passed",
            "Database schema update successful",
            "Configuration reload completed",
            "All systems operational"
        ]
        level = "INFO"
    elif scenario == "warning":
        messages = [
            "Elevated CPU usage during patch deployment",
            "Some requests experiencing slight delays",
            "Cache warmup taking longer than expected",
            "Non-critical service restart required"
        ]
        level = "WARN"
    elif scenario == "error":
        messages = [
            "Patch deployment step failed - retrying",
            "Database connection timeout during migration",
            "Service startup failed on first attempt",
            "Configuration validation errors detected"
        ]
        level = "ERROR"
    else:  # critical
        messages = [
            "CRITICAL: Patch rollback initiated",
            "Multiple service failures detected",
            "Database corruption risk identified",
            "System instability - immediate action required"
        ]
        level = "CRITICAL"
    
    return {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": random.choice(messages),
        "service": random.choice(["api", "database", "auth", "frontend", "cache"]),
        "patch_id": f"PATCH-{random.randint(1000, 9999)}",
        "cpu_usage": random.uniform(30, 90),
        "memory_usage": random.uniform(40, 85),
        "response_time": random.uniform(50, 500)
    }

def main():
    producer = KafkaProducer(
        bootstrap_servers=['kafka:9093'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    print("🚀 Starting patch log producer...")
    
    try:
        while True:
            log = generate_patch_log()
            producer.send('patch-logs', log)
            print(f"📤 Sent: {log['level']} - {log['message'][:50]}...")
            time.sleep(random.uniform(1, 3))
    except KeyboardInterrupt:
        print("🛑 Stopping log producer...")
    finally:
        producer.close()

if __name__ == "__main__":
    main()
