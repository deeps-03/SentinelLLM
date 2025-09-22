#!/usr/bin/env python3
"""
Test script for Multi-Model Patch Analysis System
Demonstrates patch risk assessment using sliding window, Prophet, and Isolation Forest
"""

import json
import sys
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# Add the current directory to path to import patch_analyzer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from patch_analyzer import PatchAnalyzer


def generate_sample_data():
    """Generate realistic sample data for testing"""
    print("Generating sample historical data...")
    
    historical_data = []
    base_time = datetime.now() - timedelta(days=30)
    
    # Simulate 30 days of hourly metrics
    for day in range(30):
        for hour in range(24):
            timestamp = base_time + timedelta(days=day, hours=hour)
            
            # Base metrics with daily and weekly patterns
            time_factor = hour / 24.0  # 0-1 for daily cycle
            day_of_week = timestamp.weekday()  # 0-6
            
            # Simulate realistic patterns
            # Higher usage during business hours
            business_hours_factor = 1.0
            if 9 <= hour <= 17:  # Business hours
                business_hours_factor = 1.4
            elif 22 <= hour or hour <= 6:  # Night hours
                business_hours_factor = 0.7
            
            # Monday morning spike
            monday_factor = 1.3 if day_of_week == 0 and 8 <= hour <= 11 else 1.0
            
            # Base metrics
            cpu_usage = 45 + 15 * business_hours_factor * monday_factor + np.random.normal(0, 8)
            memory_usage = 55 + 10 * business_hours_factor + np.random.normal(0, 12)
            response_time = 180 + 50 * business_hours_factor + np.random.normal(0, 30)
            error_rate = max(0, 0.5 + 0.3 * business_hours_factor + np.random.normal(0, 0.8))
            disk_io = 1000 + 500 * business_hours_factor + np.random.normal(0, 200)
            network_latency = 20 + 5 * business_hours_factor + np.random.normal(0, 5)
            
            # Add some patch-related anomalies
            patch_days = [7, 14, 21, 28]  # Weekly patches
            if day in patch_days and 10 <= hour <= 12:  # Patch deployment hours
                if np.random.random() < 0.3:  # 30% chance of issues during patch
                    cpu_usage += np.random.uniform(20, 50)
                    memory_usage += np.random.uniform(15, 35)
                    response_time += np.random.uniform(100, 400)
                    error_rate += np.random.uniform(1, 5)
                    disk_io += np.random.uniform(500, 1500)
                    network_latency += np.random.uniform(10, 30)
            
            # Occasional random spikes
            if np.random.random() < 0.02:  # 2% chance of random spike
                spike_factor = np.random.uniform(1.5, 3.0)
                cpu_usage *= spike_factor
                response_time *= spike_factor
                error_rate *= spike_factor
            
            # Ensure realistic bounds
            cpu_usage = max(0, min(100, cpu_usage))
            memory_usage = max(0, min(100, memory_usage))
            response_time = max(50, response_time)
            error_rate = max(0, error_rate)
            disk_io = max(0, disk_io)
            network_latency = max(1, network_latency)
            
            historical_data.append({
                "timestamp": timestamp,
                "metric_value": cpu_usage,  # Primary metric for time series analysis
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "response_time": response_time,
                "error_rate": error_rate,
                "disk_io": disk_io,
                "network_latency": network_latency
            })
    
    print(f"Generated {len(historical_data)} historical data points")
    return historical_data


def test_individual_models(analyzer, test_scenarios):
    """Test each model individually"""
    print("\n" + "="*60)
    print("TESTING INDIVIDUAL MODELS")
    print("="*60)
    
    for scenario_name, metrics in test_scenarios.items():
        print(f"\n--- Testing Scenario: {scenario_name} ---")
        
        # Test Sliding Window
        if "metric_value" in metrics:
            sw_result = analyzer.sliding_window.add_data_point(
                metrics["metric_value"], 
                metrics.get("timestamp", datetime.now())
            )
            print(f"Sliding Window Result: {sw_result['risk']} (conf: {sw_result['confidence']:.3f})")
            if sw_result["detected"]:
                print(f"  Detected: {sw_result['detected']}")
        
        # Test Prophet (if trained)
        if analyzer.prophet.is_trained and "metric_value" in metrics:
            prophet_result = analyzer.prophet.predict_anomaly(
                metrics.get("timestamp", datetime.now()),
                metrics["metric_value"]
            )
            print(f"Prophet Result: {prophet_result['risk']} (conf: {prophet_result['confidence']:.3f})")
            if prophet_result["detected"]:
                print(f"  Detected: {prophet_result['detected']}")
        
        # Test Isolation Forest (if trained)
        if analyzer.isolation_forest.is_trained:
            features = {k: v for k, v in metrics.items() 
                       if k not in ["timestamp"] and isinstance(v, (int, float))}
            if_result = analyzer.isolation_forest.detect_anomaly(features)
            print(f"Isolation Forest Result: {if_result['risk']} (conf: {if_result['confidence']:.3f})")
            if if_result["detected"]:
                print(f"  Detected: {if_result['detected']}")


def test_patch_scenarios():
    """Test various patch scenarios"""
    print("Setting up Patch Analyzer...")
    
    # Configuration for testing
    config = {
        "sliding_window_size": 100,
        "ema_alpha": 0.3,
        "threshold_std": 2.0,  # More sensitive for testing
        "prophet_changepoint_scale": 0.05,
        "isolation_contamination": 0.15,  # Expect 15% anomalies
        "isolation_estimators": 50,  # Fewer trees for faster testing
        "model_weights": {
            "sliding_window": 0.35,
            "prophet": 0.35,
            "isolation_forest": 0.30
        }
    }
    
    analyzer = PatchAnalyzer(config)
    
    # Generate and prepare historical data
    historical_data = generate_sample_data()
    success = analyzer.prepare_models(historical_data)
    
    if not success:
        print("❌ Failed to prepare models properly")
        return
    
    print("✅ Models prepared successfully")
    
    # Define test scenarios
    test_scenarios = {
        "Normal Operation": {
            "timestamp": datetime.now(),
            "metric_value": 52.3,
            "cpu_usage": 52.3,
            "memory_usage": 61.2,
            "response_time": 195.5,
            "error_rate": 0.8,
            "disk_io": 1150,
            "network_latency": 22.1
        },
        
        "High CPU Spike": {
            "timestamp": datetime.now(),
            "metric_value": 91.7,
            "cpu_usage": 91.7,
            "memory_usage": 65.8,
            "response_time": 312.4,
            "error_rate": 2.1,
            "disk_io": 1680,
            "network_latency": 28.3
        },
        
        "Monday Morning Patch": {
            "timestamp": datetime.now().replace(hour=10, minute=30, second=0, microsecond=0),
            "metric_value": 87.3,
            "cpu_usage": 87.3,
            "memory_usage": 89.1,
            "response_time": 445.2,
            "error_rate": 4.7,
            "disk_io": 2100,
            "network_latency": 35.6
        },
        
        "Memory Exhaustion": {
            "timestamp": datetime.now(),
            "metric_value": 78.2,
            "cpu_usage": 78.2,
            "memory_usage": 96.8,
            "response_time": 523.7,
            "error_rate": 6.3,
            "disk_io": 890,
            "network_latency": 41.2
        },
        
        "Database Timeout Pattern": {
            "timestamp": datetime.now(),
            "metric_value": 45.6,
            "cpu_usage": 45.6,
            "memory_usage": 58.3,
            "response_time": 2100.5,  # Very high response time
            "error_rate": 12.4,
            "disk_io": 3500,
            "network_latency": 156.7
        },
        
        "Network Latency Issues": {
            "timestamp": datetime.now(),
            "metric_value": 61.2,
            "cpu_usage": 61.2,
            "memory_usage": 67.4,
            "response_time": 298.1,
            "error_rate": 3.2,
            "disk_io": 1200,
            "network_latency": 189.5  # Very high latency
        },
        
        "Off-Hours Deployment": {
            "timestamp": datetime.now().replace(hour=23, minute=45, second=0, microsecond=0),
            "metric_value": 71.8,
            "cpu_usage": 71.8,
            "memory_usage": 82.1,
            "response_time": 367.9,
            "error_rate": 5.8,
            "disk_io": 1950,
            "network_latency": 31.4
        }
    }
    
    # Test individual models first
    test_individual_models(analyzer, test_scenarios)
    
    # Test integrated analysis
    print("\n" + "="*60)
    print("INTEGRATED PATCH ANALYSIS RESULTS")
    print("="*60)
    
    results_summary = []
    
    for scenario_name, metrics in test_scenarios.items():
        print(f"\n{'='*40}")
        print(f"SCENARIO: {scenario_name}")
        print(f"{'='*40}")
        
        result = analyzer.analyze_patch_metrics(metrics)
        
        # Pretty print the result
        print(f"🎯 RISK LEVEL: {result['predicted_risk_level']}")
        print(f"📊 CONFIDENCE: {result['confidence']:.3f}")
        print(f"⏰ ANALYSIS TIME: {result['patch_time']}")
        
        if result['expected_anomalies']:
            print(f"⚠️  DETECTED ANOMALIES:")
            for anomaly in result['expected_anomalies']:
                print(f"   • {anomaly}")
        else:
            print("✅ No anomalies detected")
        
        print(f"🤖 MODEL CONSENSUS: {result.get('consensus_models', 0)}/{len(result.get('individual_predictions', {}))}")
        
        # Show individual model votes
        if 'model_votes' in result:
            print(f"📈 MODEL VOTES: HIGH={result['model_votes']['HIGH']:.2f}, "
                  f"MED={result['model_votes']['MEDIUM']:.2f}, "
                  f"LOW={result['model_votes']['LOW']:.2f}")
        
        results_summary.append({
            "scenario": scenario_name,
            "risk": result['predicted_risk_level'],
            "confidence": result['confidence'],
            "anomalies_count": len(result['expected_anomalies'])
        })
    
    # Summary table
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print(f"{'Scenario':<25} {'Risk':<8} {'Confidence':<12} {'Anomalies'}")
    print("-" * 60)
    
    for summary in results_summary:
        print(f"{summary['scenario']:<25} {summary['risk']:<8} "
              f"{summary['confidence']:<12.3f} {summary['anomalies_count']}")
    
    # Save models for future use
    model_path = "patch_analyzer_models.pkl"
    analyzer.save_models(model_path)
    print(f"\n💾 Models saved to: {model_path}")
    
    # Test model loading
    new_analyzer = PatchAnalyzer()
    if new_analyzer.load_models(model_path):
        print("✅ Model loading test successful")
    else:
        print("❌ Model loading test failed")
    
    return analyzer, results_summary


def run_performance_test(analyzer):
    """Test performance with multiple concurrent analyses"""
    print("\n" + "="*60)
    print("PERFORMANCE TEST")
    print("="*60)
    
    import time
    
    # Generate multiple test scenarios
    test_metrics = []
    for i in range(100):
        metrics = {
            "timestamp": datetime.now() - timedelta(minutes=i),
            "metric_value": 50 + np.random.normal(0, 20),
            "cpu_usage": 50 + np.random.normal(0, 20),
            "memory_usage": 60 + np.random.normal(0, 15),
            "response_time": 200 + np.random.normal(0, 50),
            "error_rate": max(0, np.random.normal(1, 2)),
            "disk_io": 1000 + np.random.normal(0, 300),
            "network_latency": 25 + np.random.normal(0, 10)
        }
        test_metrics.append(metrics)
    
    # Performance test
    start_time = time.time()
    
    for i, metrics in enumerate(test_metrics):
        result = analyzer.analyze_patch_metrics(metrics)
        if i % 20 == 0:
            print(f"Processed {i+1}/100 analyses...")
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / len(test_metrics)
    
    print(f"\n📈 PERFORMANCE RESULTS:")
    print(f"   Total analyses: {len(test_metrics)}")
    print(f"   Total time: {total_time:.3f} seconds")
    print(f"   Average time per analysis: {avg_time*1000:.1f} ms")
    print(f"   Throughput: {len(test_metrics)/total_time:.1f} analyses/second")


def main():
    """Main test function"""
    print("🚀 Starting Multi-Model Patch Analysis System Test")
    print("="*60)
    
    try:
        # Run main test scenarios
        analyzer, results = test_patch_scenarios()
        
        # Run performance test
        run_performance_test(analyzer)
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*60)
        
        # Quick usage example
        print("\n📋 QUICK USAGE EXAMPLE:")
        print("="*30)
        print("""
# Initialize analyzer
analyzer = PatchAnalyzer()

# Prepare with historical data
analyzer.prepare_models(historical_data)

# Analyze current metrics
current_metrics = {
    "timestamp": datetime.now(),
    "cpu_usage": 85.7,
    "memory_usage": 78.2,
    "response_time": 420.5,
    "error_rate": 3.1
}

result = analyzer.analyze_patch_metrics(current_metrics)
print(f"Risk Level: {result['predicted_risk_level']}")
print(f"Confidence: {result['confidence']}")
        """)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
