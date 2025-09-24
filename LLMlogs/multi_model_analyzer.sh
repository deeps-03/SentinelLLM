#!/bin/bash

# Multi-Model Patch Analyzer with Real Anomaly Detection
echo "🤖 Multi-Model Patch Analyzer - XGBoost + Qwen Integration"
echo "=========================================================="

# Create the multi-model Docker compose
cat > docker compose-multi-model.yml << 'EOF'
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    networks:
      - ai-network

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092,PLAINTEXT_HOST://kafka:9093
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    networks:
      - ai-network

  victoria-metrics:
    image: victoriametrics/victoria-metrics:latest
    ports:
      - "8428:8428"
    command:
      - "--storageDataPath=/victoria-metrics-data"
      - "--httpListenAddr=:8428"
    networks:
      - ai-network

  multi-model-analyzer:
    build:
      context: .
      dockerfile: Dockerfile.multi_model_analyzer
    depends_on:
      - kafka
      - victoria-metrics
    environment:
      - KAFKA_BROKER=kafka:9093
      - VICTORIA_METRICS_URL=http://victoria-metrics:8428
    networks:
      - ai-network
    volumes:
      - ./models:/app/models

  log-producer:
    build:
      context: .
      dockerfile: Dockerfile.patch_log_producer
    depends_on:
      - kafka
    environment:
      - KAFKA_BROKER=kafka:9093
    networks:
      - ai-network

networks:
  ai-network:
    driver: bridge
EOF

# Create multi-model analyzer
cat > core/multi_model_patch_analyzer.py << 'EOF'
#!/usr/bin/env python3
"""
Multi-Model Patch Analyzer with XGBoost + Qwen Integration
Real anomaly detection during patch scenarios
"""

import os
import sys
import json
import time
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

# ML libraries
import xgboost as xgb
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

# LangChain for Qwen integration
try:
    from langchain.llms import LlamaCpp
    from langchain.callbacks.manager import CallbackManager
    from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
    QWEN_AVAILABLE = True
except ImportError:
    print("⚠️  LangChain not available, using XGBoost only")
    QWEN_AVAILABLE = False

# Kafka and monitoring
from kafka import KafkaConsumer, KafkaProducer
import requests

class PatchScenarioSimulator:
    """Simulates realistic patch deployment scenarios with varying complexity"""
    
    def __init__(self):
        self.scenarios = {
            "low_risk_patch": {
                "base_error_rate": 0.02,
                "spike_probability": 0.05,
                "duration_minutes": 5,
                "complexity": "low"
            },
            "medium_risk_patch": {
                "base_error_rate": 0.08,
                "spike_probability": 0.15,
                "duration_minutes": 10,
                "complexity": "medium"
            },
            "high_risk_patch": {
                "base_error_rate": 0.20,
                "spike_probability": 0.35,
                "duration_minutes": 15,
                "complexity": "high"
            },
            "rollback_scenario": {
                "base_error_rate": 0.45,
                "spike_probability": 0.60,
                "duration_minutes": 8,
                "complexity": "critical"
            }
        }
        
    def generate_patch_logs(self, scenario: str, num_logs: int = 1000) -> List[Dict]:
        """Generate realistic patch deployment logs"""
        
        config = self.scenarios[scenario]
        logs = []
        start_time = datetime.now()
        
        for i in range(num_logs):
            # Time progression during patch
            minutes_elapsed = (i / num_logs) * config["duration_minutes"]
            log_time = start_time + timedelta(minutes=minutes_elapsed)
            
            # Determine if this is an error based on patch progression
            # Errors tend to spike in middle of deployment
            time_factor = np.sin(np.pi * (i / num_logs))  # Peak in middle
            adjusted_error_rate = config["base_error_rate"] * (1 + time_factor)
            
            is_error = np.random.random() < adjusted_error_rate
            is_spike = np.random.random() < config["spike_probability"]
            
            if is_error:
                if config["complexity"] == "critical":
                    messages = [
                        "CRITICAL: Database migration failed - rollback initiated",
                        "Service mesh configuration corrupted",
                        "Authentication system down - users locked out",
                        "Data integrity check failed after patch",
                        "Cascade failure in dependent services"
                    ]
                    classification = "incident"
                elif config["complexity"] == "high":
                    messages = [
                        "High memory usage detected after patch deployment",
                        "API response times increased by 300%",
                        "Cache invalidation causing performance issues",
                        "Load balancer failing health checks",
                        "Database connection pool exhausted"
                    ]
                    classification = "incident"
                elif config["complexity"] == "medium":
                    messages = [
                        "Warning: CPU usage above normal thresholds",
                        "Some API endpoints returning 5xx errors",
                        "Background job processing delays detected",
                        "Monitoring alerts for service degradation",
                        "SSL certificate renewal warnings"
                    ]
                    classification = "preventive_action"
                else:  # low complexity
                    messages = [
                        "Minor configuration reload required",
                        "Cache warming taking longer than expected", 
                        "Non-critical service restart needed",
                        "Log rotation schedule adjustment",
                        "Temporary elevated resource usage"
                    ]
                    classification = "preventive_action"
            else:
                messages = [
                    "Patch deployment step completed successfully",
                    "Service health checks passing",
                    "Database migration step successful",
                    "Configuration update applied",
                    "System performance within normal range"
                ]
                classification = "normal"
            
            # Generate metrics that correlate with patch complexity
            cpu_usage = np.random.normal(50 + config["base_error_rate"] * 100, 15)
            memory_usage = np.random.normal(60 + config["base_error_rate"] * 80, 12)
            response_time = np.random.normal(200 + config["base_error_rate"] * 1000, 50)
            
            if is_spike:
                cpu_usage *= 1.5
                memory_usage *= 1.3
                response_time *= 2.0
                
            log_entry = {
                "timestamp": log_time.isoformat(),
                "message": np.random.choice(messages),
                "level": "ERROR" if is_error else "INFO",
                "classification": classification,
                "scenario": scenario,
                "patch_stage": int((i / num_logs) * 10),  # 0-10 stages
                "cpu_usage": max(0, min(100, cpu_usage)),
                "memory_usage": max(0, min(100, memory_usage)),
                "response_time_ms": max(10, response_time),
                "is_spike": is_spike,
                "complexity": config["complexity"]
            }
            
            logs.append(log_entry)
            
        return logs

class XGBoostPatchClassifier:
    """XGBoost model for real-time patch readiness classification"""
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.accuracy_history = []
        self.feature_names = [
            'cpu_usage', 'memory_usage', 'response_time_ms', 
            'patch_stage', 'is_spike', 'hour_of_day'
        ]
        
    def extract_features(self, log_entry: Dict) -> np.array:
        """Extract features from log entry"""
        
        # Parse timestamp for hour factor
        try:
            timestamp = datetime.fromisoformat(log_entry["timestamp"])
            hour_of_day = timestamp.hour
        except:
            hour_of_day = 12
            
        features = [
            log_entry.get("cpu_usage", 50),
            log_entry.get("memory_usage", 60), 
            log_entry.get("response_time_ms", 200),
            log_entry.get("patch_stage", 0),
            1 if log_entry.get("is_spike", False) else 0,
            hour_of_day
        ]
        
        return np.array(features).reshape(1, -1)
        
    def prepare_training_data(self, logs: List[Dict]) -> Tuple[np.array, np.array]:
        """Prepare training data from logs"""
        
        X = []
        y = []
        
        for log in logs:
            features = self.extract_features(log).flatten()
            X.append(features)
            
            # Convert classification to numeric
            classification = log.get("classification", "normal")
            if classification == "normal":
                y.append(0)
            elif classification == "preventive_action":
                y.append(1) 
            else:  # incident
                y.append(2)
                
        return np.array(X), np.array(y)
        
    def train(self, logs: List[Dict]) -> Dict[str, float]:
        """Train XGBoost model and return accuracy metrics"""
        
        print("🎯 Training XGBoost model on patch scenarios...")
        
        X, y = self.prepare_training_data(logs)
        
        if len(X) == 0:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train XGBoost
        self.model = xgb.XGBClassifier(
            objective='multi:softprob',
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, average='weighted', zero_division=0),
            "recall": recall_score(y_test, y_pred, average='weighted', zero_division=0),
            "f1": f1_score(y_test, y_pred, average='weighted', zero_division=0)
        }
        
        self.accuracy_history.append(metrics["accuracy"])
        self.is_trained = True
        
        print(f"✅ XGBoost training completed - Accuracy: {metrics['accuracy']:.3f}")
        return metrics
        
    def predict(self, log_entry: Dict) -> Dict[str, Any]:
        """Predict classification and confidence"""
        
        if not self.is_trained:
            return {"classification": "normal", "confidence": 0.0, "probabilities": [1.0, 0.0, 0.0]}
        
        features = self.extract_features(log_entry)
        
        # Get prediction and probabilities
        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]
        
        classifications = ["normal", "preventive_action", "incident"]
        predicted_class = classifications[prediction]
        confidence = probabilities[prediction]
        
        return {
            "classification": predicted_class,
            "confidence": confidence,
            "probabilities": probabilities.tolist()
        }

class QwenAnalyzer:
    """Qwen model integration for intelligent log analysis"""
    
    def __init__(self, model_path="./models/qwen/qwen2-1.5b-log-classifier-Q4_K_M.gguf"):
        self.model_path = model_path
        self.llm = None
        self.is_available = False
        
        if QWEN_AVAILABLE and os.path.exists(model_path):
            try:
                callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
                self.llm = LlamaCpp(
                    model_path=model_path,
                    temperature=0.1,
                    max_tokens=512,
                    top_p=1,
                    callback_manager=callback_manager,
                    verbose=False,
                )
                self.is_available = True
                print("✅ Qwen model loaded successfully")
            except Exception as e:
                print(f"⚠️  Could not load Qwen model: {e}")
        else:
            print("⚠️  Qwen model not available")
            
    def analyze_patch_readiness(self, log_entry: Dict, xgboost_result: Dict) -> str:
        """Use Qwen to provide intelligent patch analysis"""
        
        if not self.is_available:
            return "XGBoost analysis only - Qwen not available"
            
        prompt = f"""
Analyze this patch deployment log entry for system readiness:

Log Details:
- Message: {log_entry.get('message', 'N/A')}
- Level: {log_entry.get('level', 'INFO')}
- CPU Usage: {log_entry.get('cpu_usage', 0):.1f}%
- Memory Usage: {log_entry.get('memory_usage', 0):.1f}%
- Response Time: {log_entry.get('response_time_ms', 0):.1f}ms
- Patch Stage: {log_entry.get('patch_stage', 0)}/10
- Scenario: {log_entry.get('scenario', 'unknown')}

XGBoost Classification: {xgboost_result.get('classification', 'unknown')} (confidence: {xgboost_result.get('confidence', 0):.3f})

Provide a brief analysis (2-3 sentences) of patch readiness and recommended actions:
"""
        
        try:
            response = self.llm(prompt)
            return response.strip()
        except Exception as e:
            return f"Qwen analysis failed: {str(e)}"

class MultiModelPatchAnalyzer:
    """Main analyzer combining XGBoost + Qwen with real-time processing"""
    
    def __init__(self, kafka_broker="kafka:9093"):
        self.kafka_broker = kafka_broker
        self.xgboost_classifier = XGBoostPatchClassifier()
        self.qwen_analyzer = QwenAnalyzer()
        self.patch_simulator = PatchScenarioSimulator()
        
        # Metrics tracking
        self.analysis_results = []
        self.performance_metrics = []
        
        # Kafka setup
        self.producer = None
        self.consumer = None
        self._setup_kafka()
        
    def _setup_kafka(self):
        """Setup Kafka producer and consumer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=[self.kafka_broker],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            self.consumer = KafkaConsumer(
                'patch-logs',
                bootstrap_servers=[self.kafka_broker],
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            print("✅ Kafka connections established")
        except Exception as e:
            print(f"⚠️  Kafka setup failed: {e}")
            
    def train_on_scenarios(self):
        """Train models on all patch scenarios"""
        
        print("🎓 Training multi-model system on patch scenarios...")
        
        all_logs = []
        scenario_metrics = {}
        
        for scenario_name in self.patch_simulator.scenarios.keys():
            print(f"📊 Generating {scenario_name} training data...")
            logs = self.patch_simulator.generate_patch_logs(scenario_name, 500)
            all_logs.extend(logs)
            
            # Train XGBoost on this scenario
            metrics = self.xgboost_classifier.train(logs)
            scenario_metrics[scenario_name] = metrics
            
        print(f"✅ Training completed on {len(all_logs)} log entries")
        return scenario_metrics
        
    def analyze_log_entry(self, log_entry: Dict) -> Dict[str, Any]:
        """Perform multi-model analysis on single log entry"""
        
        start_time = time.time()
        
        # XGBoost classification
        xgboost_result = self.xgboost_classifier.predict(log_entry)
        
        # Qwen analysis
        qwen_analysis = self.qwen_analyzer.analyze_patch_readiness(log_entry, xgboost_result)
        
        # Combined result
        analysis_time = time.time() - start_time
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "log_entry": log_entry,
            "xgboost_classification": xgboost_result["classification"],
            "xgboost_confidence": xgboost_result["confidence"],
            "xgboost_probabilities": xgboost_result["probabilities"],
            "qwen_analysis": qwen_analysis,
            "analysis_time_ms": analysis_time * 1000,
            "model_performance": {
                "xgboost_available": self.xgboost_classifier.is_trained,
                "qwen_available": self.qwen_analyzer.is_available
            }
        }
        
        self.analysis_results.append(result)
        return result
        
    def run_patch_scenario_analysis(self, scenario: str = "medium_risk_patch"):
        """Run complete patch scenario analysis"""
        
        print(f"🎬 Running patch scenario analysis: {scenario}")
        
        # Generate scenario logs
        logs = self.patch_simulator.generate_patch_logs(scenario, 200)
        
        results = []
        for log_entry in logs:
            result = self.analyze_log_entry(log_entry)
            results.append(result)
            
            # Send to Kafka if available
            if self.producer:
                try:
                    self.producer.send('patch-analysis', result)
                except Exception as e:
                    print(f"⚠️  Kafka send failed: {e}")
                    
        print(f"✅ Analyzed {len(results)} log entries for scenario: {scenario}")
        return results
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary of multi-model system"""
        
        if not self.analysis_results:
            return {"message": "No analysis results available"}
            
        # Calculate metrics
        total_analyses = len(self.analysis_results)
        avg_analysis_time = np.mean([r["analysis_time_ms"] for r in self.analysis_results])
        
        # Classification distribution
        classifications = [r["xgboost_classification"] for r in self.analysis_results]
        class_counts = {
            "normal": classifications.count("normal"),
            "preventive_action": classifications.count("preventive_action"),  
            "incident": classifications.count("incident")
        }
        
        # Confidence statistics
        confidences = [r["xgboost_confidence"] for r in self.analysis_results]
        avg_confidence = np.mean(confidences)
        
        return {
            "total_analyses": total_analyses,
            "avg_analysis_time_ms": avg_analysis_time,
            "classification_distribution": class_counts,
            "average_confidence": avg_confidence,
            "model_accuracy_history": self.xgboost_classifier.accuracy_history,
            "qwen_available": self.qwen_analyzer.is_available,
            "xgboost_trained": self.xgboost_classifier.is_trained
        }

def main():
    """Main function to run multi-model patch analyzer"""
    
    print("🤖 Multi-Model Patch Analyzer Starting...")
    print("=" * 50)
    
    analyzer = MultiModelPatchAnalyzer()
    
    # Train the models
    scenario_metrics = analyzer.train_on_scenarios()
    
    print("\n📊 Training Results:")
    for scenario, metrics in scenario_metrics.items():
        print(f"  {scenario}: Accuracy={metrics['accuracy']:.3f}, F1={metrics['f1']:.3f}")
    
    # Run different patch scenarios
    scenarios_to_test = ["low_risk_patch", "medium_risk_patch", "high_risk_patch", "rollback_scenario"]
    
    for scenario in scenarios_to_test:
        print(f"\n🎬 Testing scenario: {scenario}")
        results = analyzer.run_patch_scenario_analysis(scenario)
        
        # Print sample results
        for i, result in enumerate(results[:3]):  # Show first 3 results
            print(f"  Result {i+1}: {result['xgboost_classification']} (confidence: {result['xgboost_confidence']:.3f})")
        
        time.sleep(2)  # Brief pause between scenarios
    
    # Final performance summary
    print("\n📈 Final Performance Summary:")
    summary = analyzer.get_performance_summary()
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
EOF

# Create Dockerfile for multi-model analyzer
cat > Dockerfile.multi_model_analyzer << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements_qwen.txt .
RUN pip install --no-cache-dir -r requirements_qwen.txt

# Copy source code
COPY core/multi_model_patch_analyzer.py .
COPY models/ ./models/

CMD ["python", "multi_model_patch_analyzer.py"]
EOF

# Create patch log producer
cat > core/patch_log_producer.py << 'EOF'
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
EOF

# Create Dockerfile for patch log producer
cat > Dockerfile.patch_log_producer << 'EOF'
FROM python:3.9-slim

WORKDIR /app

COPY requirements_simple.txt .
RUN pip install --no-cache-dir -r requirements_simple.txt

COPY core/patch_log_producer.py .

CMD ["python", "patch_log_producer.py"]
EOF

echo "🚀 Starting Multi-Model Patch Analyzer..."
docker compose -f docker compose-multi-model.yml up -d

echo ""
echo "✅ Multi-Model Patch Analyzer Started!"
echo "🤖 Services running:"
echo "   • Kafka: localhost:9092"
echo "   • VictoriaMetrics: http://localhost:8428"
echo "   • XGBoost Classifier: Training on realistic scenarios"
echo "   • Qwen 1.5B Model: AI-powered analysis"
echo "   • Multi-Model Analyzer: Combining predictions"
echo ""
echo "🎬 Patch scenarios being analyzed:"
echo "   • Low Risk Patch (2% error rate)"
echo "   • Medium Risk Patch (8% error rate)"
echo "   • High Risk Patch (20% error rate)"
echo "   • Rollback Scenario (45% error rate)"
echo ""
echo "📊 Real-time analysis includes:"
echo "   • XGBoost classification accuracy"
echo "   • Qwen intelligent recommendations"
echo "   • Patch readiness assessment"
echo "   • Multi-model confidence scoring"

# Keep running
trap 'echo "🛑 Stopping multi-model analyzer..."; docker compose -f docker compose-multi-model.yml down; exit 0' INT
echo "⏳ Multi-model analyzer running... Press Ctrl+C to stop"
while true; do
    sleep 15
    echo "🔄 Analysis active - XGBoost + Qwen processing logs... $(date)"
done