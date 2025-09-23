#!/usr/bin/env python3
"""
Multi-Model Patch Analysis System
Combines Sliding Window + EMA, Prophet, and Isolation Forest for patch readiness assessment
"""

import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from prophet import Prophet
import joblib

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlidingWindowEMA:
    """Exponential Moving Average with Sliding Window for short-term spike detection"""
    
    def __init__(self, window_size: int = 50, alpha: float = 0.3, threshold_std: float = 2.5):
        self.window_size = window_size
        self.alpha = alpha  # EMA smoothing factor
        self.threshold_std = threshold_std
        self.history = []
        self.ema_values = []
        
    def add_data_point(self, value: float, timestamp: datetime) -> Dict[str, Any]:
        """Add new data point and detect anomalies"""
        self.history.append((timestamp, value))
        
        # Keep only window_size recent points
        if len(self.history) > self.window_size:
            self.history = self.history[-self.window_size:]
        
        # Calculate EMA
        if len(self.ema_values) == 0:
            ema = value
        else:
            ema = self.alpha * value + (1 - self.alpha) * self.ema_values[-1]
        
        self.ema_values.append(ema)
        
        # Keep EMA history aligned with data
        if len(self.ema_values) > self.window_size:
            self.ema_values = self.ema_values[-self.window_size:]
        
        # Anomaly detection
        return self._detect_anomaly(value, timestamp)
    
    def _detect_anomaly(self, current_value: float, timestamp: datetime) -> Dict[str, Any]:
        """Detect if current value is anomalous"""
        if len(self.history) < 10:  # Need minimum data
            return {
                "risk": "LOW",
                "confidence": 0.1,
                "detected": [],
                "details": "Insufficient data for analysis"
            }
        
        values = [v for _, v in self.history]
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        # Z-score anomaly detection
        z_score = abs(current_value - mean_val) / (std_val + 1e-8)
        
        # EMA trend analysis
        if len(self.ema_values) >= 5:
            recent_trend = np.mean(np.diff(self.ema_values[-5:]))
        else:
            recent_trend = 0
        
        detected_anomalies = []
        risk_level = "LOW"
        confidence = 0.5
        
        # Spike detection
        if z_score > self.threshold_std:
            detected_anomalies.append(f"Value spike detected (z-score: {z_score:.2f})")
            risk_level = "HIGH" if z_score > 3.5 else "MEDIUM"
            confidence = min(0.9, z_score / 4.0)
        
        # Trend analysis
        if abs(recent_trend) > std_val * 0.5:
            trend_type = "increasing" if recent_trend > 0 else "decreasing"
            detected_anomalies.append(f"Unusual {trend_type} trend detected")
            if risk_level == "LOW":
                risk_level = "MEDIUM"
            confidence = max(confidence, 0.7)
        
        return {
            "risk": risk_level,
            "confidence": confidence,
            "detected": detected_anomalies,
            "details": {
                "z_score": z_score,
                "recent_trend": recent_trend,
                "current_value": current_value,
                "mean": mean_val,
                "std": std_val
            }
        }


class ProphetTimeSeriesAnalyzer:
    """Prophet-based time series forecasting for recurring anomalies"""
    
    def __init__(self, changepoint_prior_scale: float = 0.05):
        self.model = None
        self.is_trained = False
        self.changepoint_prior_scale = changepoint_prior_scale
        self.historical_data = []
        
    def add_historical_data(self, data: List[Tuple[datetime, float]]):
        """Add historical data for training"""
        self.historical_data.extend(data)
        
    def train(self) -> bool:
        """Train Prophet model on historical data"""
        if len(self.historical_data) < 20:  # Need minimum data for Prophet
            logger.warning("Insufficient historical data for Prophet training")
            return False
        
        # Prepare data for Prophet
        df = pd.DataFrame(self.historical_data, columns=['ds', 'y'])
        df['ds'] = pd.to_datetime(df['ds'])
        
        try:
            self.model = Prophet(
                changepoint_prior_scale=self.changepoint_prior_scale,
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=True,
                interval_width=0.95
            )
            self.model.fit(df)
            self.is_trained = True
            logger.info("Prophet model trained successfully")
            return True
        except Exception as e:
            logger.error(f"Prophet training failed: {e}")
            return False
    
    def predict_anomaly(self, timestamp: datetime, actual_value: float) -> Dict[str, Any]:
        """Predict if current value is anomalous based on time series patterns"""
        if not self.is_trained:
            return {
                "risk": "LOW",
                "confidence": 0.1,
                "detected": [],
                "details": "Model not trained"
            }
        
        try:
            # Create future dataframe for prediction
            future_df = pd.DataFrame({'ds': [timestamp]})
            forecast = self.model.predict(future_df)
            
            predicted_value = forecast['yhat'].iloc[0]
            lower_bound = forecast['yhat_lower'].iloc[0]
            upper_bound = forecast['yhat_upper'].iloc[0]
            
            detected_anomalies = []
            risk_level = "LOW"
            confidence = 0.5
            
            # Check if actual value is outside prediction interval
            if actual_value < lower_bound or actual_value > upper_bound:
                deviation = max(
                    abs(actual_value - lower_bound) / (upper_bound - lower_bound + 1e-8),
                    abs(actual_value - upper_bound) / (upper_bound - lower_bound + 1e-8)
                )
                
                detected_anomalies.append(f"Value outside predicted range: {actual_value:.2f} vs [{lower_bound:.2f}, {upper_bound:.2f}]")
                
                if deviation > 2:
                    risk_level = "HIGH"
                    confidence = 0.85
                elif deviation > 1:
                    risk_level = "MEDIUM"
                    confidence = 0.7
            
            # Check for recurring patterns
            hour = timestamp.hour
            day_of_week = timestamp.weekday()
            
            # Analyze if this time typically has issues
            if self._is_problematic_time(hour, day_of_week):
                detected_anomalies.append(f"Historically problematic time detected: {timestamp.strftime('%A %H:%M')}")
                if risk_level == "LOW":
                    risk_level = "MEDIUM"
                confidence = max(confidence, 0.75)
            
            return {
                "risk": risk_level,
                "confidence": confidence,
                "detected": detected_anomalies,
                "details": {
                    "predicted_value": predicted_value,
                    "actual_value": actual_value,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "deviation": abs(actual_value - predicted_value)
                }
            }
            
        except Exception as e:
            logger.error(f"Prophet prediction failed: {e}")
            return {
                "risk": "LOW",
                "confidence": 0.1,
                "detected": [],
                "details": f"Prediction error: {e}"
            }
    
    def _is_problematic_time(self, hour: int, day_of_week: int) -> bool:
        """Check if this time historically has issues"""
        # Common problematic times for patches:
        # - Monday mornings (0 = Monday)
        # - Peak hours (9-11 AM, 2-4 PM)
        # - Late night deployments (10 PM - 2 AM)
        
        if day_of_week == 0 and 8 <= hour <= 12:  # Monday morning
            return True
        if hour in [9, 10, 11, 14, 15, 16]:  # Peak hours
            return True
        if hour >= 22 or hour <= 2:  # Late night
            return True
        
        return False


class IsolationForestAnomalyDetector:
    """Isolation Forest for detecting novel/unusual anomalies"""
    
    def __init__(self, contamination: float = 0.1, n_estimators: int = 100):
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
        
    def train(self, training_data: List[Dict[str, float]]) -> bool:
        """Train Isolation Forest on normal behavior data"""
        if len(training_data) < 50:
            logger.warning("Insufficient training data for Isolation Forest")
            return False
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(training_data)
            self.feature_names = df.columns.tolist()
            
            # Scale features
            X_scaled = self.scaler.fit_transform(df)
            
            # Train model
            self.model.fit(X_scaled)
            self.is_trained = True
            logger.info("Isolation Forest trained successfully")
            return True
            
        except Exception as e:
            logger.error(f"Isolation Forest training failed: {e}")
            return False
    
    def detect_anomaly(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Detect if current features represent an anomaly"""
        if not self.is_trained:
            return {
                "risk": "LOW",
                "confidence": 0.1,
                "detected": [],
                "details": "Model not trained"
            }
        
        try:
            # Prepare features
            feature_vector = []
            for feature_name in self.feature_names:
                feature_vector.append(features.get(feature_name, 0.0))
            
            # Scale features
            X_scaled = self.scaler.transform([feature_vector])
            
            # Predict anomaly
            anomaly_score = self.model.decision_function(X_scaled)[0]
            is_anomaly = self.model.predict(X_scaled)[0] == -1
            
            detected_anomalies = []
            risk_level = "LOW"
            confidence = 0.5
            
            if is_anomaly:
                detected_anomalies.append(f"Novel anomaly pattern detected (score: {anomaly_score:.3f})")
                
                # Risk level based on anomaly score (more negative = more anomalous)
                if anomaly_score < -0.5:
                    risk_level = "HIGH"
                    confidence = 0.8
                elif anomaly_score < -0.2:
                    risk_level = "MEDIUM"
                    confidence = 0.65
                else:
                    risk_level = "MEDIUM"
                    confidence = 0.5
            
            return {
                "risk": risk_level,
                "confidence": confidence,
                "detected": detected_anomalies,
                "details": {
                    "anomaly_score": anomaly_score,
                    "is_anomaly": is_anomaly,
                    "features": features
                }
            }
            
        except Exception as e:
            logger.error(f"Isolation Forest prediction failed: {e}")
            return {
                "risk": "LOW",
                "confidence": 0.1,
                "detected": [],
                "details": f"Prediction error: {e}"
            }


class MetaClassifier:
    """Aggregator/Meta-Classifier to combine outputs from all models"""
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "sliding_window": 0.3,
            "prophet": 0.4,
            "isolation_forest": 0.3
        }
        self.risk_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        self.reverse_risk_levels = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}
    
    def aggregate_predictions(self, predictions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Combine predictions from all models into final assessment"""
        
        # Count votes for each risk level
        risk_votes = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        total_confidence = 0
        all_detected = []
        model_details = {}
        
        for model_name, prediction in predictions.items():
            risk = prediction.get("risk", "LOW")
            confidence = prediction.get("confidence", 0.0)
            detected = prediction.get("detected", [])
            
            # Weight the vote by confidence and model weight
            weight = self.weights.get(model_name, 1.0)
            weighted_confidence = confidence * weight
            
            risk_votes[risk] += weighted_confidence
            total_confidence += weighted_confidence
            all_detected.extend([f"{model_name}: {d}" for d in detected])
            model_details[model_name] = prediction
        
        # Determine final risk level
        if risk_votes["HIGH"] >= 0.6:  # High threshold for HIGH risk
            final_risk = "HIGH"
        elif risk_votes["HIGH"] + risk_votes["MEDIUM"] >= 0.4:  # Combined threshold for MEDIUM
            final_risk = "MEDIUM"
        else:
            final_risk = "LOW"
        
        # Calculate overall confidence
        final_confidence = total_confidence / len(predictions) if predictions else 0.0
        
        # Apply consensus bonus (if multiple models agree)
        consensus_count = sum(1 for p in predictions.values() if p.get("risk") == final_risk)
        if consensus_count >= 2:
            final_confidence = min(0.95, final_confidence * 1.2)
        
        # Extract unique anomaly types
        unique_anomalies = list(set([
            detected.split(": ", 1)[-1] if ": " in detected else detected 
            for detected in all_detected
        ]))
        
        return {
            "patch_time": datetime.now().isoformat(),
            "predicted_risk_level": final_risk,
            "expected_anomalies": unique_anomalies,
            "confidence": round(final_confidence, 3),
            "model_votes": risk_votes,
            "individual_predictions": model_details,
            "consensus_models": consensus_count
        }


class PatchAnalyzer:
    """Main class that orchestrates all models for patch analysis"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize models
        self.sliding_window = SlidingWindowEMA(
            window_size=self.config.get("sliding_window_size", 50),
            alpha=self.config.get("ema_alpha", 0.3),
            threshold_std=self.config.get("threshold_std", 2.5)
        )
        
        self.prophet = ProphetTimeSeriesAnalyzer(
            changepoint_prior_scale=self.config.get("prophet_changepoint_scale", 0.05)
        )
        
        self.isolation_forest = IsolationForestAnomalyDetector(
            contamination=self.config.get("isolation_contamination", 0.1),
            n_estimators=self.config.get("isolation_estimators", 100)
        )
        
        self.meta_classifier = MetaClassifier(
            weights=self.config.get("model_weights")
        )
        
        self.is_ready = False
        
    def prepare_models(self, historical_data: List[Dict[str, Any]]) -> bool:
        """Prepare all models with historical data"""
        logger.info("Preparing models with historical data...")
        
        try:
            # Prepare time series data for Prophet
            time_series_data = []
            feature_data = []
            
            for record in historical_data:
                timestamp = record.get("timestamp")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                # For time series (Prophet)
                if "metric_value" in record:
                    time_series_data.append((timestamp, record["metric_value"]))
                
                # For feature-based detection (Isolation Forest)
                features = {k: v for k, v in record.items() 
                           if k not in ["timestamp", "is_anomaly"] and isinstance(v, (int, float))}
                if features:
                    feature_data.append(features)
            
            # Train Prophet
            if time_series_data:
                self.prophet.add_historical_data(time_series_data)
                prophet_trained = self.prophet.train()
            else:
                prophet_trained = False
                logger.warning("No time series data available for Prophet")
            
            # Train Isolation Forest
            if feature_data:
                isolation_trained = self.isolation_forest.train(feature_data)
            else:
                isolation_trained = False
                logger.warning("No feature data available for Isolation Forest")
            
            self.is_ready = True  # At least sliding window works without training
            logger.info(f"Models prepared: Prophet={prophet_trained}, IsolationForest={isolation_trained}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare models: {e}")
            return False
    
    def analyze_patch_metrics(self, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current patch metrics using all models"""
        if not self.is_ready:
            logger.error("Models not prepared. Call prepare_models() first.")
            return {"error": "Models not ready"}
        
        timestamp = current_metrics.get("timestamp", datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        predictions = {}
        
        # 1. Sliding Window + EMA Analysis
        if "metric_value" in current_metrics:
            sliding_result = self.sliding_window.add_data_point(
                current_metrics["metric_value"], 
                timestamp
            )
            predictions["sliding_window"] = sliding_result
        
        # 2. Prophet Analysis
        if "metric_value" in current_metrics and self.prophet.is_trained:
            prophet_result = self.prophet.predict_anomaly(
                timestamp, 
                current_metrics["metric_value"]
            )
            predictions["prophet"] = prophet_result
        
        # 3. Isolation Forest Analysis
        features = {k: v for k, v in current_metrics.items() 
                   if k not in ["timestamp"] and isinstance(v, (int, float))}
        if features and self.isolation_forest.is_trained:
            isolation_result = self.isolation_forest.detect_anomaly(features)
            predictions["isolation_forest"] = isolation_result
        
        # 4. Meta-Classification
        if predictions:
            final_result = self.meta_classifier.aggregate_predictions(predictions)
            return final_result
        else:
            return {
                "patch_time": timestamp.isoformat(),
                "predicted_risk_level": "LOW",
                "expected_anomalies": [],
                "confidence": 0.1,
                "error": "No valid predictions generated"
            }
    
    def save_models(self, filepath: str):
        """Save trained models"""
        model_data = {
            "sliding_window": {
                "history": self.sliding_window.history,
                "ema_values": self.sliding_window.ema_values,
                "config": {
                    "window_size": self.sliding_window.window_size,
                    "alpha": self.sliding_window.alpha,
                    "threshold_std": self.sliding_window.threshold_std
                }
            },
            "isolation_forest": {
                "model": self.isolation_forest.model if self.isolation_forest.is_trained else None,
                "scaler": self.isolation_forest.scaler if self.isolation_forest.is_trained else None,
                "feature_names": self.isolation_forest.feature_names,
                "is_trained": self.isolation_forest.is_trained
            },
            "config": self.config
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"Models saved to {filepath}")
    
    def load_models(self, filepath: str):
        """Load trained models"""
        try:
            model_data = joblib.load(filepath)
            
            # Restore sliding window
            if "sliding_window" in model_data:
                sw_data = model_data["sliding_window"]
                self.sliding_window.history = sw_data.get("history", [])
                self.sliding_window.ema_values = sw_data.get("ema_values", [])
                if "config" in sw_data:
                    config = sw_data["config"]
                    self.sliding_window.window_size = config.get("window_size", 50)
                    self.sliding_window.alpha = config.get("alpha", 0.3)
                    self.sliding_window.threshold_std = config.get("threshold_std", 2.5)
            
            # Restore isolation forest
            if "isolation_forest" in model_data:
                if_data = model_data["isolation_forest"]
                if if_data.get("is_trained") and if_data.get("model"):
                    self.isolation_forest.model = if_data["model"]
                    self.isolation_forest.scaler = if_data["scaler"]
                    self.isolation_forest.feature_names = if_data.get("feature_names", [])
                    self.isolation_forest.is_trained = True
            
            self.is_ready = True
            logger.info(f"Models loaded from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            return False


def main():
    """Example usage of the PatchAnalyzer"""
    
    # Configuration
    config = {
        "sliding_window_size": 50,
        "ema_alpha": 0.3,
        "threshold_std": 2.5,
        "prophet_changepoint_scale": 0.05,
        "isolation_contamination": 0.1,
        "isolation_estimators": 100,
        "model_weights": {
            "sliding_window": 0.3,
            "prophet": 0.4,
            "isolation_forest": 0.3
        }
    }
    
    # Initialize analyzer
    analyzer = PatchAnalyzer(config)
    
    # Example historical data (you would load this from your actual logs)
    historical_data = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(100):
        timestamp = base_time + timedelta(hours=i)
        # Simulate normal metrics with some noise
        cpu_usage = 50 + np.random.normal(0, 10)
        memory_usage = 60 + np.random.normal(0, 15)
        response_time = 200 + np.random.normal(0, 50)
        
        # Add some anomalies
        if i in [20, 45, 78]:  # Simulate patch days with issues
            cpu_usage += 40
            memory_usage += 30
            response_time += 300
        
        historical_data.append({
            "timestamp": timestamp,
            "metric_value": cpu_usage,  # Primary metric for time series
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "response_time": response_time,
            "error_rate": max(0, np.random.normal(1, 2))
        })
    
    # Prepare models
    success = analyzer.prepare_models(historical_data)
    if not success:
        logger.error("Failed to prepare models")
        return
    
    # Analyze current patch metrics
    current_metrics = {
        "timestamp": datetime.now(),
        "metric_value": 95,  # High CPU usage
        "cpu_usage": 95,
        "memory_usage": 85,
        "response_time": 450,
        "error_rate": 3.5
    }
    
    result = analyzer.analyze_patch_metrics(current_metrics)
    
    print("\n" + "="*60)
    print("PATCH ANALYSIS RESULT")
    print("="*60)
    print(json.dumps(result, indent=2, default=str))
    
    # Save models for future use
    analyzer.save_models("patch_analyzer_models.pkl")


if __name__ == "__main__":
    main()
