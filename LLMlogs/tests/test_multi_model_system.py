#!/usr/bin/env python3
"""
Test script for the Multi-Model Anomaly Detection System

This script demonstrates and tests the integration of:
1. Sliding Window + EMA detection
2. Prophet time-series forecasting 
3. Isolation Forest anomaly detection
4. Qwen LLM integration for log classification and patch readiness
"""

import os
import sys
import time
import json
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

try:
    from multi_model_anomaly_detector import (
        SlidingWindowEMADetector,
        ProphetDetector, 
        IsolationForestDetector,
        MetaClassifier,
        MultiModelAnomalyDetector
    )
    from qwen_patch_readiness import (
        QwenLogClassifier,
        IntegratedPatchReadinessSystem
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required dependencies are installed.")
    sys.exit(1)

class MultiModelTester:
    """Test suite for the multi-model anomaly detection system"""
    
    def __init__(self):
        self.test_results = {}
        
    def test_sliding_window_ema(self):
        """Test the Sliding Window + EMA detector"""
        print("\n=== Testing Sliding Window + EMA Detector ===")
        
        detector = SlidingWindowEMADetector(window_size=10, alpha=0.3, threshold_multiplier=2.0)
        
        # Generate test data with a spike
        normal_data = np.random.normal(50, 5, 20)  # Normal values around 50
        spike_data = [150, 140, 130]  # Sudden spike
        test_data = np.concatenate([normal_data, spike_data])
        
        results = []
        for i, value in enumerate(test_data):
            result = detector.update(value)
            results.append(result)
            print(f"Value {i+1}: {value:.2f} -> Risk: {result['risk']}, Confidence: {result['confidence']:.2f}")
            
            if result['detected']:
                for anomaly in result['detected']:
                    print(f"  ⚠️  {anomaly}")
        
        # Check if spikes were detected
        spike_detected = any(r['risk'] in ['HIGH', 'MEDIUM'] for r in results[-3:])
        
        self.test_results['sliding_window_ema'] = {
            'passed': spike_detected,
            'message': "Spike detection" if spike_detected else "Failed to detect spike"
        }
        
        print(f"Result: {'✅ PASSED' if spike_detected else '❌ FAILED'}")
        
    def test_prophet_detector(self):
        """Test the Prophet detector"""
        print("\n=== Testing Prophet Detector ===")
        
        detector = ProphetDetector()
        
        # Generate synthetic time series data with daily pattern
        timestamps = []
        values = []
        base_time = datetime.now() - timedelta(days=30)
        
        for i in range(720):  # 30 days of hourly data
            timestamp = base_time + timedelta(hours=i)
            # Daily pattern with some noise
            hour = timestamp.hour
            daily_pattern = 50 + 20 * np.sin(2 * np.pi * hour / 24)
            noise = np.random.normal(0, 2)
            value = daily_pattern + noise
            
            timestamps.append(timestamp)
            values.append(value)
        
        # Train the model
        print("Training Prophet model...")
        training_success = detector.train(timestamps, values)
        
        if training_success:
            print("✅ Prophet model trained successfully")
            
            # Test prediction with normal value
            test_time = datetime.now()
            normal_value = 60  # Within expected range
            result_normal = detector.predict(test_time, normal_value)
            
            # Test prediction with anomalous value
            anomalous_value = 200  # Way outside expected range
            result_anomaly = detector.predict(test_time, anomalous_value)
            
            print(f"Normal value test: Risk={result_normal['risk']}, Confidence={result_normal['confidence']:.2f}")
            print(f"Anomalous value test: Risk={result_anomaly['risk']}, Confidence={result_anomaly['confidence']:.2f}")
            
            anomaly_detected = result_anomaly['risk'] in ['HIGH', 'MEDIUM']
            normal_correct = result_normal['risk'] == 'LOW'
            
            self.test_results['prophet'] = {
                'passed': training_success and anomaly_detected and normal_correct,
                'message': f"Training: {training_success}, Anomaly Detection: {anomaly_detected}, Normal Classification: {normal_correct}"
            }
            
            print(f"Result: {'✅ PASSED' if training_success and anomaly_detected else '❌ FAILED'}")
        else:
            print("❌ Prophet model training failed")
            self.test_results['prophet'] = {
                'passed': False,
                'message': "Model training failed"
            }
    
    def test_isolation_forest(self):
        """Test the Isolation Forest detector"""
        print("\n=== Testing Isolation Forest Detector ===")
        
        detector = IsolationForestDetector(contamination=0.1)
        
        # Generate training data (normal behavior)
        training_data = []
        for i in range(100):
            metrics = {
                'cpu_usage': np.random.normal(50, 10),
                'memory_usage': np.random.normal(60, 8),
                'disk_usage': np.random.normal(70, 5),
                'network_io': np.random.normal(1000, 100),
                'error_rate': np.random.normal(2, 0.5),
                'response_time': np.random.normal(0.2, 0.05),
                'request_count': np.random.normal(100, 20)
            }
            training_data.append(metrics)
        
        # Train the model
        print("Training Isolation Forest...")
        training_success = detector.train(training_data)
        
        if training_success:
            print("✅ Isolation Forest trained successfully")
            
            # Test with normal metrics
            normal_metrics = {
                'cpu_usage': 55,
                'memory_usage': 65,
                'disk_usage': 72,
                'network_io': 950,
                'error_rate': 2.1,
                'response_time': 0.21,
                'request_count': 95
            }
            result_normal = detector.detect(normal_metrics)
            
            # Test with anomalous metrics
            anomalous_metrics = {
                'cpu_usage': 95,  # Very high
                'memory_usage': 90,  # Very high
                'disk_usage': 98,  # Very high
                'network_io': 5000,  # Very high
                'error_rate': 50,  # Very high
                'response_time': 2.0,  # Very high
                'request_count': 10  # Very low
            }
            result_anomaly = detector.detect(anomalous_metrics)
            
            print(f"Normal metrics test: Risk={result_normal['risk']}, Score={result_normal.get('anomaly_score', 0):.3f}")
            print(f"Anomalous metrics test: Risk={result_anomaly['risk']}, Score={result_anomaly.get('anomaly_score', 0):.3f}")
            
            anomaly_detected = result_anomaly['is_anomaly']
            normal_correct = not result_normal['is_anomaly']
            
            self.test_results['isolation_forest'] = {
                'passed': training_success and anomaly_detected,
                'message': f"Training: {training_success}, Anomaly Detection: {anomaly_detected}, Normal Classification: {normal_correct}"
            }
            
            print(f"Result: {'✅ PASSED' if training_success and anomaly_detected else '❌ FAILED'}")
        else:
            print("❌ Isolation Forest training failed")
            self.test_results['isolation_forest'] = {
                'passed': False,
                'message': "Model training failed"
            }
    
    def test_meta_classifier(self):
        """Test the Meta-Classifier"""
        print("\n=== Testing Meta-Classifier ===")
        
        meta_classifier = MetaClassifier(voting_threshold=2)
        
        # Test Case 1: High risk from multiple models
        results_high_risk = {
            'sliding_window': {'risk': 'HIGH', 'confidence': 0.8, 'detected': ['CPU spike']},
            'prophet': {'risk': 'HIGH', 'confidence': 0.9, 'detected': ['Unusual pattern']},
            'isolation_forest': {'risk': 'MEDIUM', 'confidence': 0.6, 'detected': ['Anomalous metrics']}
        }
        
        aggregated_high = meta_classifier.aggregate_results(results_high_risk)
        print(f"High risk test: Final Risk={aggregated_high['predicted_risk_level']}, Confidence={aggregated_high['confidence']:.2f}")
        
        # Test Case 2: Low risk from all models
        results_low_risk = {
            'sliding_window': {'risk': 'LOW', 'confidence': 0.1, 'detected': []},
            'prophet': {'risk': 'LOW', 'confidence': 0.2, 'detected': []},
            'isolation_forest': {'risk': 'LOW', 'confidence': 0.1, 'detected': []}
        }
        
        aggregated_low = meta_classifier.aggregate_results(results_low_risk)
        print(f"Low risk test: Final Risk={aggregated_low['predicted_risk_level']}, Confidence={aggregated_low['confidence']:.2f}")
        
        # Validate results
        high_risk_correct = aggregated_high['predicted_risk_level'] == 'HIGH'
        low_risk_correct = aggregated_low['predicted_risk_level'] == 'LOW'
        
        self.test_results['meta_classifier'] = {
            'passed': high_risk_correct and low_risk_correct,
            'message': f"High risk classification: {high_risk_correct}, Low risk classification: {low_risk_correct}"
        }
        
        print(f"Result: {'✅ PASSED' if high_risk_correct and low_risk_correct else '❌ FAILED'}")
    
    def test_integrated_system(self):
        """Test the integrated multi-model system"""
        print("\n=== Testing Integrated Multi-Model System ===")
        
        # Note: This test uses mock data since it doesn't require external dependencies
        try:
            detector = MultiModelAnomalyDetector()
            
            # Override the fetch_metrics method for testing
            def mock_fetch_metrics():
                return {
                    'cpu_usage': 75,  # Slightly elevated
                    'memory_usage': 80,  # Elevated
                    'disk_usage': 70,
                    'network_io': 1200,
                    'error_rate': 5,  # Elevated
                    'response_time': 0.3,
                    'request_count': 120
                }
            
            detector.fetch_metrics = mock_fetch_metrics
            
            print("Running integrated anomaly detection...")
            result = detector.detect_anomalies()
            
            # Check if result has expected structure
            expected_keys = ['patch_time', 'predicted_risk_level', 'expected_anomalies', 'confidence', 'current_metrics']
            has_expected_structure = all(key in result for key in expected_keys)
            
            print(f"Risk Level: {result.get('predicted_risk_level', 'N/A')}")
            print(f"Confidence: {result.get('confidence', 0):.2f}")
            print(f"Anomalies: {len(result.get('expected_anomalies', []))}")
            
            self.test_results['integrated_system'] = {
                'passed': has_expected_structure,
                'message': f"Structure validation: {has_expected_structure}"
            }
            
            print(f"Result: {'✅ PASSED' if has_expected_structure else '❌ FAILED'}")
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            self.test_results['integrated_system'] = {
                'passed': False,
                'message': f"Exception: {str(e)}"
            }
    
    def test_llm_integration(self):
        """Test LLM integration (without actually loading the model)"""
        print("\n=== Testing LLM Integration Structure ===")
        
        try:
            # Test the structure without loading the actual model
            classifier = QwenLogClassifier()
            
            # Test prompt generation
            sample_logs = [
                "ERROR: Database connection failed",
                "WARNING: High memory usage: 85%",
                "INFO: Service started successfully"
            ]
            
            anomaly_context = {
                'predicted_risk_level': 'MEDIUM',
                'confidence': 0.7,
                'expected_anomalies': ['Database connectivity issue'],
                'current_metrics': {'error_rate': 5.2}
            }
            
            # Test prompt creation
            classification_prompt = classifier.create_log_classification_prompt(sample_logs, anomaly_context)
            readiness_prompt = classifier.create_patch_readiness_prompt({}, anomaly_context)
            
            prompt_created = len(classification_prompt) > 100 and len(readiness_prompt) > 100
            
            self.test_results['llm_integration'] = {
                'passed': prompt_created,
                'message': f"Prompt generation: {prompt_created} (Note: Model not loaded for testing)"
            }
            
            print(f"Prompt generation test: {'✅ PASSED' if prompt_created else '❌ FAILED'}")
            print("Note: Actual LLM inference not tested (requires model download)")
            
        except Exception as e:
            print(f"❌ LLM integration test failed: {e}")
            self.test_results['llm_integration'] = {
                'passed': False,
                'message': f"Exception: {str(e)}"
            }
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting Multi-Model Anomaly Detection System Tests")
        print("=" * 60)
        
        test_methods = [
            self.test_sliding_window_ema,
            self.test_prophet_detector,
            self.test_isolation_forest,
            self.test_meta_classifier,
            self.test_integrated_system,
            self.test_llm_integration
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                test_name = test_method.__name__
                print(f"❌ {test_name} failed with exception: {e}")
                self.test_results[test_name] = {
                    'passed': False,
                    'message': f"Exception: {str(e)}"
                }
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🧪 TEST SUMMARY")
        print("=" * 60)
        
        passed_count = 0
        total_count = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result['passed'] else "❌ FAILED"
            print(f"{test_name:25} {status:10} {result['message']}")
            if result['passed']:
                passed_count += 1
        
        print("=" * 60)
        print(f"Overall Result: {passed_count}/{total_count} tests passed")
        
        if passed_count == total_count:
            print("🎉 All tests passed! The multi-model system is ready.")
        else:
            print("⚠️  Some tests failed. Please check the implementation.")

def demo_system_workflow():
    """Demonstrate the complete workflow"""
    print("\n🚀 MULTI-MODEL ANOMALY DETECTION WORKFLOW DEMO")
    print("=" * 60)
    
    # Simulate patch deployment scenario
    print("Scenario: Pre-patch deployment anomaly assessment")
    print("\n1. Multi-Model Anomaly Detection Results:")
    
    mock_anomaly_result = {
        "patch_time": datetime.now().isoformat(),
        "predicted_risk_level": "MEDIUM",
        "expected_anomalies": ["CPU spike detected", "Memory usage above threshold"],
        "confidence": 0.73,
        "model_votes": {
            "high_risk": 1,
            "medium_risk": 2,
            "total_models": 3
        },
        "individual_results": {
            "sliding_window": {
                "risk": "MEDIUM",
                "confidence": 0.7,
                "detected": ["CPU spike detected"]
            },
            "prophet": {
                "risk": "MEDIUM", 
                "confidence": 0.8,
                "detected": ["Memory usage above threshold"]
            },
            "isolation_forest": {
                "risk": "LOW",
                "confidence": 0.4,
                "detected": []
            }
        },
        "current_metrics": {
            "cpu_usage": 75,
            "memory_usage": 82,
            "error_rate": 4.2
        }
    }
    
    print(json.dumps(mock_anomaly_result, indent=2, default=str))
    
    print("\n2. Patch Readiness Assessment:")
    print("📋 PATCH DEPLOYMENT DECISION: PROCEED WITH CAUTION")
    print("🎯 Risk Level: MEDIUM (Confidence: 0.73)")
    print("⚠️  Detected Issues:")
    print("   • CPU spike detected during monitoring window")
    print("   • Memory usage above normal threshold")
    print("\n💡 Recommendations:")
    print("   • Monitor CPU and memory usage closely during deployment")
    print("   • Consider deploying during low-traffic window")
    print("   • Have rollback plan ready")
    print("   • Set up additional alerting for resource usage")
    
    print("\n3. Integration Points:")
    print("   ✅ Kafka topics: patch_anomalies, patch_readiness_assessments")
    print("   ✅ Grafana dashboards: Multi-model anomaly detection")
    print("   ✅ Alert manager: Risk-based alert routing")
    print("   ✅ LLM analysis: Intelligent decision support")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        demo_system_workflow()
    else:
        tester = MultiModelTester()
        tester.run_all_tests()
        
        if len(sys.argv) > 1 and sys.argv[1] == '--with-demo':
            demo_system_workflow()
