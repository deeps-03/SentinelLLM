"""
Multi-Model Anomaly Detection System for Patch Readiness Assessment

This system combines three different anomaly detection approaches:
1. Sliding Window + EMA: For detecting short-term spikes
2. Prophet: For detecting seasonal/recurring anomalies 
3. Isolation Forest: For detecting novel/unusual anomalies

The outputs are combined by a meta-classifier to provide robust anomaly detection.
"""

import os
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import warnings

# ML and anomaly detection imports
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from prophet import Prophet
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import LSTM, Dense, Input, RepeatVector, TimeDistributed
from tensorflow.keras.optimizers import Adam

# Kafka and monitoring imports
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import NoBrokersAvailable
import requests
from dotenv import load_dotenv

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')
tf.get_logger().setLevel('ERROR')

# Load environment variables
load_dotenv()

class SlidingWindowEMADetector:
    """
    Sliding Window + Exponential Moving Average Detector
    Good for: Short-term spikes during patch (sudden CPU/memory jumps)
    Weakness: Doesn't see long-term cycles
    """
    
    def __init__(self, window_size: int = 20, alpha: float = 0.3, threshold_multiplier: float = 2.0):
        self.window_size = window_size
        self.alpha = alpha  # EMA smoothing factor
        self.threshold_multiplier = threshold_multiplier
        self.data_buffer = []
        self.ema_values = []
        self.std_values = []
        
    def update(self, value: float) -> Dict[str, Any]:
        """Update the detector with a new value and check for anomalies"""
        self.data_buffer.append(value)
        
        # Maintain sliding window
        if len(self.data_buffer) > self.window_size:
            self.data_buffer.pop(0)
            
        if len(self.data_buffer) < 5:  # Need minimum data points
            return {"risk": "LOW", "confidence": 0.0, "detected": []}
            
        # Calculate EMA
        if not self.ema_values:
            ema = np.mean(self.data_buffer)
        else:
            ema = self.alpha * value + (1 - self.alpha) * self.ema_values[-1]
            
        self.ema_values.append(ema)
        
        # Calculate rolling standard deviation
        window_std = np.std(self.data_buffer)
        self.std_values.append(window_std)
        
        # Detect anomalies
        threshold = ema + self.threshold_multiplier * window_std
        is_anomaly = value > threshold
        
        anomalies = []
        risk_level = "LOW"
        confidence = 0.0
        
        if is_anomaly and window_std > 0:
            deviation = (value - ema) / window_std
            confidence = min(deviation / self.threshold_multiplier, 1.0)
            
            if deviation > 3:
                risk_level = "HIGH"
                anomalies.append(f"Severe spike detected (z-score: {deviation:.2f})")
            elif deviation > 2:
                risk_level = "MEDIUM" 
                anomalies.append(f"Moderate spike detected (z-score: {deviation:.2f})")
            else:
                risk_level = "LOW"
                
        return {
            "risk": risk_level,
            "confidence": confidence,
            "detected": anomalies,
            "current_value": value,
            "ema": ema,
            "threshold": threshold
        }

class ProphetDetector:
    """
    Prophet Time-Series Forecasting Detector
    Good for: Daily/weekly recurring patch anomalies
    Weakness: Struggles with sudden outliers/one-off events
    """
    
    def __init__(self, seasonality_mode: str = 'multiplicative'):
        self.model = None
        self.is_trained = False
        self.seasonality_mode = seasonality_mode
        self.min_data_points = 50  # Minimum data points needed for training
        
    def train(self, timestamps: List[datetime], values: List[float]) -> bool:
        """Train the Prophet model on historical data"""
        if len(timestamps) < self.min_data_points:
            return False
            
        try:
            # Prepare data for Prophet
            df = pd.DataFrame({
                'ds': timestamps,
                'y': values
            })
            
            # Initialize and fit Prophet model
            self.model = Prophet(
                seasonality_mode=self.seasonality_mode,
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,
                changepoint_prior_scale=0.05
            )
            
            self.model.fit(df)
            self.is_trained = True
            return True
            
        except Exception as e:
            print(f"Error training Prophet model: {e}")
            return False
    
    def predict(self, timestamp: datetime, actual_value: float) -> Dict[str, Any]:
        """Predict and detect anomalies using the trained model"""
        if not self.is_trained:
            return {"risk": "LOW", "confidence": 0.0, "detected": []}
            
        try:
            # Create future dataframe for prediction
            future_df = pd.DataFrame({'ds': [timestamp]})
            forecast = self.model.predict(future_df)
            
            predicted_value = forecast['yhat'].iloc[0]
            lower_bound = forecast['yhat_lower'].iloc[0] 
            upper_bound = forecast['yhat_upper'].iloc[0]
            
            # Check if actual value is outside prediction interval
            is_anomaly = actual_value < lower_bound or actual_value > upper_bound
            
            anomalies = []
            risk_level = "LOW"
            confidence = 0.0
            
            if is_anomaly:
                # Calculate deviation from prediction
                prediction_range = upper_bound - lower_bound
                if prediction_range > 0:
                    if actual_value > upper_bound:
                        deviation = (actual_value - upper_bound) / prediction_range
                        anomalies.append(f"Value above predicted range (deviation: {deviation:.2f})")
                    else:
                        deviation = (lower_bound - actual_value) / prediction_range
                        anomalies.append(f"Value below predicted range (deviation: {deviation:.2f})")
                    
                    confidence = min(deviation, 1.0)
                    
                    if deviation > 1.5:
                        risk_level = "HIGH"
                    elif deviation > 0.8:
                        risk_level = "MEDIUM"
                    else:
                        risk_level = "LOW"
            
            return {
                "risk": risk_level,
                "confidence": confidence,
                "detected": anomalies,
                "predicted_value": predicted_value,
                "actual_value": actual_value,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound
            }
            
        except Exception as e:
            print(f"Error in Prophet prediction: {e}")
            return {"risk": "LOW", "confidence": 0.0, "detected": []}

class IsolationForestDetector:
    """
    Isolation Forest Anomaly Detector
    Good for: Unusual or novel patch failures that don't match history
    Weakness: May over-trigger false positives if logs are noisy
    """
    
    def __init__(self, contamination: float = 0.1, n_estimators: int = 100):
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_history = []
        self.min_training_samples = 50
        
    def extract_features(self, metrics: Dict[str, float]) -> np.array:
        """Extract features from metrics for anomaly detection"""
        features = []
        
        # Basic metrics
        features.extend([
            metrics.get('cpu_usage', 0),
            metrics.get('memory_usage', 0),
            metrics.get('disk_usage', 0),
            metrics.get('network_io', 0),
            metrics.get('error_rate', 0),
            metrics.get('response_time', 0),
            metrics.get('request_count', 0), 0)
        ])
        
        # Derived features
        features.append(metrics.get('cpu_usage', 0) * metrics.get('memory_usage', 0))  # CPU-Memory interaction
        features.append(metrics.get('error_rate', 0) / max(metrics.get('request_count', 1), 1))  # Error density
        
        return np.array(features).reshape(1, -1)
    
    def train(self, historical_metrics: List[Dict[str, float]]) -> bool:
        """Train the Isolation Forest model on historical metrics"""
        if len(historical_metrics) < self.min_training_samples:
            return False
            
        try:
            # Extract features from historical data
            feature_matrix = []
            for metrics in historical_metrics:
                features = self.extract_features(metrics)
                feature_matrix.append(features.flatten())
                
            feature_matrix = np.array(feature_matrix)
            
            # Scale features
            feature_matrix_scaled = self.scaler.fit_transform(feature_matrix)
            
            # Train Isolation Forest
            self.model.fit(feature_matrix_scaled)
            self.is_trained = True
            return True
            
        except Exception as e:
            print(f"Error training Isolation Forest: {e}")
            return False
    
    def detect(self, current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Detect anomalies in current metrics"""
        if not self.is_trained:
            return {"risk": "LOW", "confidence": 0.0, "detected": []}
            
        try:
            # Extract and scale features
            features = self.extract_features(current_metrics)
            features_scaled = self.scaler.transform(features)
            
            # Get anomaly score
            anomaly_score = self.model.decision_function(features_scaled)[0]
            is_anomaly = self.model.predict(features_scaled)[0] == -1
            
            anomalies = []
            risk_level = "LOW"
            confidence = 0.0
            
            if is_anomaly:
                # Convert anomaly score to confidence (more negative = more anomalous)
                confidence = min(abs(anomaly_score) / 0.5, 1.0)  # Normalize to 0-1
                
                if anomaly_score < -0.3:
                    risk_level = "HIGH"
                    anomalies.append(f"Novel anomaly detected (score: {anomaly_score:.3f})")
                elif anomaly_score < -0.1:
                    risk_level = "MEDIUM"
                    anomalies.append(f"Unusual pattern detected (score: {anomaly_score:.3f})")
                else:
                    risk_level = "LOW"
                    
            return {
                "risk": risk_level,
                "confidence": confidence,
                "detected": anomalies,
                "anomaly_score": anomaly_score,
                "is_anomaly": is_anomaly
            }
            
        except Exception as e:
            print(f"Error in Isolation Forest detection: {e}")
            return {"risk": "LOW", "confidence": 0.0, "detected": []}

class MetaClassifier:
    """
    Meta-Classifier that combines outputs from all three models
    Implements weighted confidence scoring based on model strengths
    """
    
    def __init__(self):
        # Model weights based on their strengths for different anomaly types
        self.model_weights = {
            'sliding_window': 0.3,   # EMA - good for sudden spikes
            'prophet': 0.4,          # Prophet - best for time-series patterns  
            'isolation_forest': 0.3  # Isolation Forest - good for novel anomalies
        }
        
        # Confidence thresholds for action levels
        self.confidence_thresholds = {
            'HIGH': 0.90,      # All 3 models agree - immediate alert + auto-escalation
            'MEDIUM': 0.70,    # 2 out of 3 models agree - alert with investigation
            'LOW': 0.50,       # 1 model detects - log for review, no immediate alert
            'NOISE': 0.0       # No consensus - filtered out
        }
        
    def calculate_weighted_confidence(self, results: Dict[str, Dict[str, Any]]) -> float:
        """
        Calculate weighted confidence score using model-specific weights
        Formula: Confidence = (Score_EMA × 0.3) + (Score_Prophet × 0.4) + (Score_IsolationForest × 0.3)
        """
        weighted_score = 0.0
        total_weight = 0.0
        
        for model_name, weight in self.model_weights.items():
            model_result = results.get(model_name, {})
            model_confidence = model_result.get('confidence', 0.0)
            
            # Convert boolean detection to confidence score if needed
            if 'detected' in model_result and isinstance(model_result['detected'], bool):
                if model_result['detected']:
                    model_confidence = max(model_confidence, 0.8)  # Minimum confidence for detection
                    
            weighted_score += model_confidence * weight
            total_weight += weight
            
        return weighted_score / max(total_weight, 1.0)
    
    def determine_action_level(self, confidence: float, model_agreement: Dict[str, int]) -> tuple:
        """Determine confidence level and recommended action based on agreement and confidence"""
        
        # Count model agreements
        high_risk_count = model_agreement.get('high_risk', 0)
        medium_risk_count = model_agreement.get('medium_risk', 0) 
        total_models = model_agreement.get('total_models', 3)
        
        # Determine base confidence level from model agreement
        if high_risk_count == total_models:  # All models agree on HIGH risk
            base_level = "HIGH"
            action = "Immediate alert + Auto-escalation"
        elif high_risk_count >= 2 or (high_risk_count >= 1 and medium_risk_count >= 1):  # 2+ models agree
            base_level = "MEDIUM" 
            action = "Alert with investigation prompt"
        elif high_risk_count >= 1 or medium_risk_count >= 1:  # At least 1 model detects
            base_level = "LOW"
            action = "Log for review, no immediate alert"
        else:  # No model consensus
            base_level = "NOISE"
            action = "Filtered out"
            
        # Apply confidence threshold adjustments
        if confidence >= self.confidence_thresholds['HIGH']:
            final_level = "HIGH"
            action = "Immediate alert + Auto-escalation"
        elif confidence >= self.confidence_thresholds['MEDIUM']:
            final_level = "MEDIUM" if base_level != "NOISE" else "LOW"
            action = "Alert with investigation prompt"
        elif confidence >= self.confidence_thresholds['LOW']:
            final_level = "LOW" if base_level != "NOISE" else "LOW"
            action = "Log for review, no immediate alert"
        else:
            final_level = "NOISE"
            action = "Filtered out"
            
        return final_level, action
        
    def aggregate_results(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from all three models using weighted confidence"""
        models = ['sliding_window', 'prophet', 'isolation_forest']
        
        # Count model agreement levels
        model_agreement = {
            'high_risk': sum(1 for model in models if results.get(model, {}).get('risk') == 'HIGH'),
            'medium_risk': sum(1 for model in models if results.get(model, {}).get('risk') == 'MEDIUM'),
            'total_models': len(models)
        }
        
        # Calculate weighted confidence
        weighted_confidence = self.calculate_weighted_confidence(results)
        
        # Determine final confidence level and action
        confidence_level, recommended_action = self.determine_action_level(
            weighted_confidence, model_agreement
        )
        
        # Collect all detected anomalies
        all_anomalies = []
        for model_name in models:
            model_result = results.get(model_name, {})
            if model_result.get('detected'):
                if isinstance(model_result['detected'], list):
                    all_anomalies.extend(model_result['detected'])
                else:
                    all_anomalies.append(f"{model_name}_anomaly")
        
        return {
            "patch_time": datetime.now().isoformat(),
            "confidence_level": confidence_level,
            "confidence_score": round(weighted_confidence, 3),
            "confidence_percentage": f"{weighted_confidence:.1%}",
            "recommended_action": recommended_action,
            "predicted_risk_level": confidence_level,
            "expected_anomalies": list(set(all_anomalies)),
            "model_agreement": model_agreement,
            "individual_results": results,
            "thresholds_used": self.confidence_thresholds
        }

class MultiModelAnomalyDetector:
    """
    Main class that orchestrates all three anomaly detection models
    """
    
    def __init__(self, kafka_broker: str = None, prometheus_url: str = None):
        # Initialize components
        self.sliding_window_detector = SlidingWindowEMADetector()
        self.prophet_detector = ProphetDetector()
        self.isolation_forest_detector = IsolationForestDetector()
        self.meta_classifier = MetaClassifier()
        
        # Configuration
        self.kafka_broker = kafka_broker or os.getenv('KAFKA_BROKER', 'kafka:9093')
        self.prometheus_url = prometheus_url or "http://victoria-metrics:8428/api/v1/query"
        
        # Initialize Kafka producer
        self.producer = None
        self._init_kafka_producer()
        
        # Data storage
        self.metrics_history = []
        self.is_initialized = False
        
    def _init_kafka_producer(self):
        """Initialize Kafka producer for publishing results"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=[self.kafka_broker],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            print("Kafka producer initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize Kafka producer: {e}")
    
    def fetch_metrics(self) -> Dict[str, float]:
        """Fetch current metrics from Prometheus/VictoriaMetrics"""
        metrics = {}
        
        try:
            # Define metric queries
            queries = {
                'cpu_usage': 'cpu_usage_percent',
                'memory_usage': 'memory_usage_percent', 
                'disk_usage': 'disk_usage_percent',
                'network_io': 'network_io_bytes_total',
                'error_rate': 'log_error_total',
                'response_time': 'http_request_duration_seconds',
                'request_count': 'http_requests_total'
            }
            
            for metric_name, query in queries.items():
                params = {"query": query}
                response = requests.get(self.prometheus_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success" and result.get("data", {}).get("result"):
                        # Get the latest value
                        latest_value = float(result["data"]["result"][0]["value"][1])
                        metrics[metric_name] = latest_value
                    else:
                        metrics[metric_name] = 0.0
                else:
                    metrics[metric_name] = 0.0
                    
        except Exception as e:
            print(f"Error fetching metrics: {e}")
            # Return default values
            metrics = {
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'disk_usage': 0.0,
                'network_io': 0.0,
                'error_rate': 0.0,
                'response_time': 0.0,
                'request_count': 0.0
            }
            
        return metrics
    
    def initialize_models(self):
        """Initialize and train models with historical data"""
        print("Initializing multi-model anomaly detection system...")
        
        # Fetch historical data for training
        historical_data = self._fetch_historical_data()
        
        if len(historical_data) > 50:  # Sufficient data for training
            print(f"Training models with {len(historical_data)} historical data points...")
            
            # Prepare data for Prophet
            timestamps = [data['timestamp'] for data in historical_data]
            error_rates = [data['metrics']['error_rate'] for data in historical_data]
            
            # Train Prophet model
            if self.prophet_detector.train(timestamps, error_rates):
                print("Prophet model trained successfully")
            else:
                print("Prophet model training failed")
            
            # Train Isolation Forest
            metrics_list = [data['metrics'] for data in historical_data]
            if self.isolation_forest_detector.train(metrics_list):
                print("Isolation Forest model trained successfully")
            else:
                print("Isolation Forest training failed")
                
        else:
            print(f"Insufficient historical data ({len(historical_data)} points). Models will use default behavior.")
            
        self.is_initialized = True
        
    def _fetch_historical_data(self) -> List[Dict]:
        """Fetch historical data for model training"""
        # This would typically fetch from a database or time-series store
        # For demo purposes, we'll generate some sample data
        historical_data = []
        
        base_time = datetime.now() - timedelta(days=7)
        
        for i in range(1000):  # 1000 data points over 7 days
            timestamp = base_time + timedelta(minutes=10*i)
            
            # Generate realistic metrics with some patterns and noise
            hour = timestamp.hour
            day_of_week = timestamp.weekday()
            
            # Simulate daily patterns (higher errors during peak hours)
            base_error_rate = 2.0 + 3.0 * np.sin(2 * np.pi * hour / 24)
            
            # Add weekly patterns (higher on weekdays)
            if day_of_week < 5:  # Weekday
                base_error_rate *= 1.2
                
            # Add noise
            error_rate = max(0, base_error_rate + np.random.normal(0, 0.5))
            
            metrics = {
                'cpu_usage': 50 + 20 * np.sin(2 * np.pi * hour / 24) + np.random.normal(0, 5),
                'memory_usage': 60 + 15 * np.sin(2 * np.pi * hour / 24) + np.random.normal(0, 3),
                'disk_usage': 70 + np.random.normal(0, 2),
                'network_io': 1000 + 500 * np.sin(2 * np.pi * hour / 24) + np.random.normal(0, 50),
                'error_rate': error_rate,
                'response_time': 0.2 + 0.1 * np.sin(2 * np.pi * hour / 24) + np.random.normal(0, 0.02),
                'request_count': 100 + 50 * np.sin(2 * np.pi * hour / 24) + np.random.normal(0, 10)
            }
            
            historical_data.append({
                'timestamp': timestamp,
                'metrics': metrics
            })
            
        return historical_data
    
    def detect_anomalies(self) -> Dict[str, Any]:
        """Run anomaly detection using all three models"""
        if not self.is_initialized:
            self.initialize_models()
            
        # Fetch current metrics
        current_metrics = self.fetch_metrics()
        current_time = datetime.now()
        
        # Store in history
        self.metrics_history.append({
            'timestamp': current_time,
            'metrics': current_metrics
        })
        
        # Keep only recent history (last 1000 points)
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        results = {}
        
        # 1. Sliding Window + EMA Detection
        error_rate = current_metrics.get('error_rate', 0)
        results['sliding_window'] = self.sliding_window_detector.update(error_rate)
        
        # 2. Prophet Detection
        results['prophet'] = self.prophet_detector.predict(current_time, error_rate)
        
        # 3. Isolation Forest Detection
        results['isolation_forest'] = self.isolation_forest_detector.detect(current_metrics)
        
        # 4. Meta-Classification
        final_result = self.meta_classifier.aggregate_results(results)
        
        # Add current metrics to result
        final_result['current_metrics'] = current_metrics
        
        return final_result
    
    def publish_result(self, result: Dict[str, Any], topic: str = 'patch_anomalies'):
        """Publish anomaly detection result to Kafka"""
        if self.producer:
            try:
                self.producer.send(topic, result)
                self.producer.flush()
                print(f"Anomaly result published to Kafka topic: {topic}")
            except Exception as e:
                print(f"Error publishing to Kafka: {e}")
    
    def run_continuous_monitoring(self, interval: int = 60):
        """Run continuous anomaly monitoring"""
        print("Starting multi-model anomaly detection monitoring...")
        
        while True:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] Running anomaly detection...")
                
                # Detect anomalies
                result = self.detect_anomalies()
                
                # Log results
                risk_level = result['predicted_risk_level']
                confidence = result['confidence']
                anomalies = result['expected_anomalies']
                
                print(f"Risk Level: {risk_level} (Confidence: {confidence:.2f})")
                
                if anomalies:
                    print("Detected Anomalies:")
                    for anomaly in anomalies:
                        print(f"  - {anomaly}")
                else:
                    print("No anomalies detected")
                
                # Publish to Kafka
                self.publish_result(result)
                
                # Sleep before next check
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\nStopping anomaly detection monitoring...")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(interval)

def main():
    """Main function to run the multi-model anomaly detector"""
    detector = MultiModelAnomalyDetector()
    
    # Run one-time detection
    if len(os.sys.argv) > 1 and os.sys.argv[1] == '--once':
        result = detector.detect_anomalies()
        print(json.dumps(result, indent=2, default=str))
    else:
        # Run continuous monitoring
        detector.run_continuous_monitoring(interval=60)

if __name__ == "__main__":
    main()
