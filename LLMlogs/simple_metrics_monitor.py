#!/usr/bin/env python3

"""
Simple Text-Based Metrics Monitor for Presentation
Shows real-time metrics in terminal without GUI dependencies
"""

import time
import json
import requests
import os
from datetime import datetime
from collections import deque
import random
import math

class SimpleMetricsMonitor:
    def __init__(self, victoria_metrics_url="http://localhost:8428/api/v1/query"):
        self.vm_url = victoria_metrics_url
        self.max_points = 20
        self.metrics_data = {
            'cpu_usage': deque(maxlen=self.max_points),
            'memory_usage': deque(maxlen=self.max_points),
            'disk_usage': deque(maxlen=self.max_points),
            'network_io': deque(maxlen=self.max_points),
            'error_rate': deque(maxlen=self.max_points),
            'response_time': deque(maxlen=self.max_points),
            'request_count': deque(maxlen=self.max_points),
            'log_classification': deque(maxlen=self.max_points),
            'ai_confidence': deque(maxlen=self.max_points)
        }
        
    def fetch_metric(self, query, default_value=0.0):
        """Fetch a single metric from VictoriaMetrics"""
        try:
            params = {"query": query}
            response = requests.get(self.vm_url, params=params, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("data", {}).get("result"):
                    return float(data["data"]["result"][0]["value"][1])
        except Exception:
            pass
            
        return default_value
        
    def generate_synthetic_data(self):
        """Generate realistic synthetic data for demo"""
        now = datetime.now()
        hour_factor = math.sin(2 * math.pi * now.hour / 24)
        
        return {
            'cpu_usage': max(0, min(100, 45 + 25 * hour_factor + random.gauss(0, 5))),
            'memory_usage': max(0, min(100, 60 + 15 * hour_factor + random.gauss(0, 3))),
            'disk_usage': max(0, min(100, 75 + random.gauss(0, 2))),
            'network_io': max(0, 50 + 30 * hour_factor + random.gauss(0, 10)),
            'error_rate': max(0, 2 + 3 * abs(hour_factor) + random.expovariate(1)),
            'response_time': max(0, 150 + 50 * abs(hour_factor) + random.gauss(0, 20)),
            'request_count': max(0, 100 + 80 * hour_factor + random.gauss(0, 15)),
            'log_classification': max(0, min(100, 85 + random.gauss(0, 5))),
            'ai_confidence': max(0, min(100, 78 + random.gauss(0, 8)))
        }
        
    def fetch_all_metrics(self):
        """Fetch all metrics or generate synthetic data"""
        metric_queries = {
            'cpu_usage': 'system_cpu_usage_percent',
            'memory_usage': 'system_memory_usage_percent',
            'disk_usage': 'system_disk_usage_percent',
            'network_io': 'system_network_io_bytes',
            'error_rate': 'log_incident_total',
            'response_time': 'log_processing_rate_per_minute',
            'request_count': 'logs_processed_total',
            'log_classification': 'log_classification_confidence_avg',
            'ai_confidence': 'anomaly_detection_alerts_total'
        }
        
        # Try real metrics first
        real_data_available = False
        metrics = {}
        
        for metric_name, query in metric_queries.items():
            value = self.fetch_metric(query)
            if value > 0:
                real_data_available = True
            metrics[metric_name] = value
            
        # Use synthetic data if no real data
        if not real_data_available:
            metrics = self.generate_synthetic_data()
            
        return metrics
        
    def create_bar_chart(self, value, width=20):
        """Create a simple ASCII bar chart"""
        if value < 0:
            value = 0
        elif value > 100:
            value = 100
            
        filled = int(value * width / 100)
        empty = width - filled
        
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {value:6.1f}%"
        
    def create_trend_line(self, values):
        """Create a simple ASCII trend indicator"""
        if len(values) < 2:
            return "→"
            
        recent = list(values)[-5:]  # Last 5 values
        if len(recent) < 2:
            return "→"
            
        # Calculate trend
        avg_recent = sum(recent[-3:]) / min(3, len(recent))
        avg_older = sum(recent[:-3]) / max(1, len(recent) - 3) if len(recent) > 3 else recent[0]
        
        diff = avg_recent - avg_older
        
        if abs(diff) < 1:
            return "→"  # Stable
        elif diff > 0:
            return "↗"  # Increasing
        else:
            return "↘"  # Decreasing
            
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def display_metrics(self, metrics):
        """Display metrics in a nice terminal format"""
        self.clear_screen()
        
        # Update data
        for metric_name, value in metrics.items():
            self.metrics_data[metric_name].append(value)
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print("=" * 80)
        print(f"🚀 SentinelLLM - Real-time Metrics Dashboard [{timestamp}]")
        print("=" * 80)
        print()
        
        # Display metrics with bars and trends
        metric_info = [
            ('cpu_usage', 'CPU Usage', '%'),
            ('memory_usage', 'Memory Usage', '%'),
            ('disk_usage', 'Disk Usage', '%'),
            ('network_io', 'Network I/O', 'MB/s'),
            ('error_rate', 'Error Rate', 'errors/min'),
            ('response_time', 'Response Time', 'ms'),
            ('request_count', 'Request Count', '/min'),
            ('log_classification', 'Log Classification Rate', '%'),
            ('ai_confidence', 'AI Confidence Score', '%')
        ]
        
        for metric_key, label, unit in metric_info:
            current_value = metrics.get(metric_key, 0)
            trend = self.create_trend_line(self.metrics_data[metric_key])
            
            # Scale for display (except percentages)
            if unit == '%':
                display_value = current_value
                bar = self.create_bar_chart(current_value)
            elif unit == 'ms':
                display_value = current_value
                # Scale response time for bar (0-500ms -> 0-100%)
                bar_value = min(100, (current_value / 500) * 100)
                bar = self.create_bar_chart(bar_value)
            elif unit == 'MB/s':
                display_value = current_value
                # Scale network IO for bar (0-100MB/s -> 0-100%)
                bar_value = min(100, current_value)
                bar = self.create_bar_chart(bar_value)
            else:
                display_value = current_value
                # Scale other metrics for bar
                max_vals = {'errors/min': 10, '/min': 200}
                max_val = max_vals.get(unit, 100)
                bar_value = min(100, (current_value / max_val) * 100)
                bar = self.create_bar_chart(bar_value)
                
            print(f"{label:<25} {trend} {bar} {display_value:8.1f} {unit}")
            
        print()
        print("=" * 80)
        
        # Status indicators
        cpu_val = metrics.get('cpu_usage', 0)
        mem_val = metrics.get('memory_usage', 0)
        error_val = metrics.get('error_rate', 0)
        
        status = "🟢 NORMAL"
        if cpu_val > 80 or mem_val > 85 or error_val > 5:
            status = "🔴 HIGH LOAD"
        elif cpu_val > 60 or mem_val > 70 or error_val > 2:
            status = "🟡 MODERATE"
            
        print(f"System Status: {status}")
        print(f"Data Source: {'🔗 VictoriaMetrics' if self.fetch_metric('up') > 0 else '🧪 Synthetic Demo Data'}")
        print()
        print("💡 Press Ctrl+C to stop monitoring")
        print("=" * 80)
        
    def run_monitoring(self, interval=3):
        """Start real-time monitoring"""
        print("🎯 Starting SentinelLLM Metrics Monitor")
        print("📊 Monitoring system performance and AI analysis metrics")
        print("=" * 60)
        
        try:
            while True:
                metrics = self.fetch_all_metrics()
                self.display_metrics(metrics)
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.clear_screen()
            print("\n🛑 Metrics monitoring stopped")
            print("✅ Thank you for using SentinelLLM!")

def main():
    monitor = SimpleMetricsMonitor()
    monitor.run_monitoring(interval=2)

if __name__ == "__main__":
    main()