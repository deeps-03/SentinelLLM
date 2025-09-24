#!/usr/bin/env python3

"""
Real-time Metrics Visualization for Presentation
Generates live graphs for: CPU, Memory, Disk, Network, Error Rate, Response Time, Request Count
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.dates import DateFormatter
import numpy as np
import requests
import json
from datetime import datetime, timedelta
import threading
import time
from collections import deque
import argparse

class MetricsVisualizer:
    def __init__(self, victoria_metrics_url="http://localhost:8428/api/v1/query"):
        self.vm_url = victoria_metrics_url
        self.fig, self.axes = plt.subplots(3, 3, figsize=(15, 10))
        self.fig.suptitle('🚀 SentinelLLM - Real-time System Metrics', fontsize=16, fontweight='bold')
        
        # Data storage (keep last 50 points)
        self.max_points = 50
        self.timestamps = deque(maxlen=self.max_points)
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
        
        # Configure subplots
        self.setup_plots()
        
        # Colors for different metrics
        self.colors = {
            'cpu_usage': '#FF6B6B',
            'memory_usage': '#4ECDC4', 
            'disk_usage': '#45B7D1',
            'network_io': '#96CEB4',
            'error_rate': '#FFEAA7',
            'response_time': '#DDA0DD',
            'request_count': '#98D8C8',
            'log_classification': '#F7DC6F',
            'ai_confidence': '#BB8FCE'
        }
        
    def setup_plots(self):
        """Setup individual plots with labels and styling"""
        plots = [
            (0, 0, 'CPU Usage (%)', 'cpu_usage'),
            (0, 1, 'Memory Usage (%)', 'memory_usage'),
            (0, 2, 'Disk Usage (%)', 'disk_usage'),
            (1, 0, 'Network I/O (MB/s)', 'network_io'),
            (1, 1, 'Error Rate (errors/min)', 'error_rate'),
            (1, 2, 'Response Time (ms)', 'response_time'),
            (2, 0, 'Request Count (/min)', 'request_count'),
            (2, 1, 'Log Classification Rate', 'log_classification'),
            (2, 2, 'AI Confidence Score', 'ai_confidence')
        ]
        
        for row, col, title, metric in plots:
            ax = self.axes[row, col]
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel('Time')
            ax.set_ylabel('Value')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 100)  # Default range
            
        # Adjust layout
        plt.tight_layout()
        
    def fetch_metric(self, query, default_value=0.0):
        """Fetch a single metric from VictoriaMetrics"""
        try:
            params = {"query": query}
            response = requests.get(self.vm_url, params=params, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("data", {}).get("result"):
                    return float(data["data"]["result"][0]["value"][1])
        except Exception as e:
            pass
            
        return default_value
        
    def generate_synthetic_data(self):
        """Generate realistic synthetic data for demo purposes"""
        now = datetime.now()
        
        # Generate synthetic but realistic metrics
        base_time = time.time()
        hour_factor = np.sin(2 * np.pi * now.hour / 24)
        
        return {
            'cpu_usage': max(0, min(100, 45 + 25 * hour_factor + np.random.normal(0, 5))),
            'memory_usage': max(0, min(100, 60 + 15 * hour_factor + np.random.normal(0, 3))),
            'disk_usage': max(0, min(100, 75 + np.random.normal(0, 2))),
            'network_io': max(0, 50 + 30 * hour_factor + np.random.normal(0, 10)),
            'error_rate': max(0, 2 + 3 * abs(hour_factor) + np.random.exponential(1)),
            'response_time': max(0, 150 + 50 * abs(hour_factor) + np.random.normal(0, 20)),
            'request_count': max(0, 100 + 80 * hour_factor + np.random.normal(0, 15)),
            'log_classification': max(0, min(100, 85 + np.random.normal(0, 5))),
            'ai_confidence': max(0, min(100, 78 + np.random.normal(0, 8)))
        }
        
    def fetch_all_metrics(self):
        """Fetch all metrics from VictoriaMetrics or generate synthetic data"""
        current_time = datetime.now()
        
        # Try to fetch real metrics first
        metrics = {}
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
        
        real_data_available = False
        for metric_name, query in metric_queries.items():
            value = self.fetch_metric(query)
            if value > 0:
                real_data_available = True
            metrics[metric_name] = value
            
        # If no real data available, use synthetic data
        if not real_data_available:
            metrics = self.generate_synthetic_data()
            
        return current_time, metrics
        
    def update_plots(self, frame):
        """Update all plots with new data"""
        timestamp, metrics = self.fetch_all_metrics()
        
        # Add new data
        self.timestamps.append(timestamp)
        for metric_name, value in metrics.items():
            self.metrics_data[metric_name].append(value)
            
        # Clear and redraw all plots
        for i, (row, col) in enumerate([(0,0), (0,1), (0,2), (1,0), (1,1), (1,2), (2,0), (2,1), (2,2)]):
            metric_names = list(self.metrics_data.keys())
            if i < len(metric_names):
                metric_name = metric_names[i]
                ax = self.axes[row, col]
                ax.clear()
                
                if len(self.timestamps) > 1:
                    x_data = list(self.timestamps)
                    y_data = list(self.metrics_data[metric_name])
                    
                    # Plot the line
                    ax.plot(x_data, y_data, 
                           color=self.colors.get(metric_name, '#333333'),
                           linewidth=2, marker='o', markersize=3)
                    
                    # Fill area under curve
                    ax.fill_between(x_data, y_data, alpha=0.3, 
                                  color=self.colors.get(metric_name, '#333333'))
                    
                    # Set titles and labels
                    titles = {
                        'cpu_usage': 'CPU Usage (%)',
                        'memory_usage': 'Memory Usage (%)',
                        'disk_usage': 'Disk Usage (%)',
                        'network_io': 'Network I/O (MB/s)',
                        'error_rate': 'Error Rate (errors/min)',
                        'response_time': 'Response Time (ms)',
                        'request_count': 'Request Count (/min)',
                        'log_classification': 'Log Classification Rate (%)',
                        'ai_confidence': 'AI Confidence Score (%)'
                    }
                    
                    ax.set_title(titles.get(metric_name, metric_name.title()), 
                               fontsize=11, fontweight='bold')
                    
                    # Set appropriate Y-axis limits
                    if metric_name in ['cpu_usage', 'memory_usage', 'disk_usage', 'log_classification', 'ai_confidence']:
                        ax.set_ylim(0, 100)
                    elif metric_name == 'response_time':
                        ax.set_ylim(0, max(300, max(y_data) * 1.1) if y_data else 300)
                    elif metric_name == 'error_rate':
                        ax.set_ylim(0, max(10, max(y_data) * 1.1) if y_data else 10)
                    else:
                        ax.set_ylim(0, max(y_data) * 1.1 if y_data else 100)
                    
                    # Format x-axis
                    ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
                    
                    # Add current value as text
                    if y_data:
                        current_value = y_data[-1]
                        ax.text(0.02, 0.98, f'Current: {current_value:.1f}',
                              transform=ax.transAxes, fontsize=10, fontweight='bold',
                              verticalalignment='top', 
                              bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='x', rotation=45, labelsize=8)
                
        plt.tight_layout()
        
    def start_visualization(self, interval=2000):
        """Start the real-time visualization"""
        print("🚀 Starting Real-time Metrics Visualization")
        print("📊 Monitoring: CPU, Memory, Disk, Network, Errors, Response Time, Requests, AI Analysis")
        print("🎯 Press Ctrl+C to stop")
        
        # Create animation
        ani = animation.FuncAnimation(
            self.fig, self.update_plots, interval=interval, blit=False, cache_frame_data=False)
        
        plt.show()

def main():
    parser = argparse.ArgumentParser(description='Real-time Metrics Visualization')
    parser.add_argument('--vm-url', default='http://localhost:8428/api/v1/query',
                       help='VictoriaMetrics URL')
    parser.add_argument('--interval', type=int, default=2000,
                       help='Update interval in milliseconds')
    
    args = parser.parse_args()
    
    print("🎯 SentinelLLM Metrics Visualization")
    print("=" * 40)
    print(f"📊 VictoriaMetrics URL: {args.vm_url}")
    print(f"⏱️  Update interval: {args.interval}ms")
    print("💡 If VictoriaMetrics is not available, synthetic data will be used")
    print("")
    
    visualizer = MetricsVisualizer(args.vm_url)
    
    try:
        visualizer.start_visualization(args.interval)
    except KeyboardInterrupt:
        print("\n🛑 Visualization stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()