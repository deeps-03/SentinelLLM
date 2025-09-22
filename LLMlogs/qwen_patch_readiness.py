"""
Qwen LLM Integration for Log Classification and Patch Readiness Assessment

This module integrates the multi-model anomaly detection results with Qwen LLM
for intelligent log classification and patch readiness recommendations.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from dataclasses import dataclass

# Import the multi-model detector
from multi_model_anomaly_detector import MultiModelAnomalyDetector

# LLM imports
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

@dataclass
class PatchReadinessReport:
    """Structure for patch readiness assessment results"""
    patch_time: str
    risk_level: str
    confidence: float
    anomalies_detected: List[str]
    log_classifications: Dict[str, Any]
    recommendations: List[str]
    preventive_actions: List[str]
    deployment_decision: str
    reasoning: str

class QwenLogClassifier:
    """
    Qwen LLM-based log classifier and patch readiness assessor
    """
    
    def __init__(self, model_name: str = "Qwen/Qwen2-7B-Instruct"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.max_length = 2048
        
        # Log classification categories
        self.log_categories = {
            "CRITICAL": "System failures that could cause outages",
            "ERROR": "Errors that impact functionality but don't cause outages", 
            "WARNING": "Potential issues that should be monitored",
            "INFO": "Informational messages about system state",
            "DEBUG": "Detailed debugging information"
        }
        
        # Risk assessment thresholds
        self.risk_thresholds = {
            "HIGH": 0.8,
            "MEDIUM": 0.5,
            "LOW": 0.3
        }
        
    def initialize_model(self):
        """Initialize the Qwen model and tokenizer"""
        try:
            print(f"Loading Qwen model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
            print("Qwen model loaded successfully")
            return True
        except Exception as e:
            print(f"Error loading Qwen model: {e}")
            return False
    
    def create_log_classification_prompt(self, log_entries: List[str], anomaly_context: Dict[str, Any]) -> str:
        """Create a prompt for log classification"""
        
        anomaly_info = f"""
Anomaly Detection Context:
- Risk Level: {anomaly_context.get('predicted_risk_level', 'UNKNOWN')}
- Confidence: {anomaly_context.get('confidence', 0.0):.2f}
- Detected Anomalies: {', '.join(anomaly_context.get('expected_anomalies', []))}
- Current Metrics: {json.dumps(anomaly_context.get('current_metrics', {}), indent=2)}
"""

        log_sample = "\n".join(log_entries[:10])  # Limit to first 10 logs
        
        prompt = f"""You are an expert system administrator analyzing logs for patch deployment readiness.

{anomaly_info}

Recent Log Entries:
{log_sample}

Please analyze these logs and provide:

1. LOG CLASSIFICATION: Classify each significant log entry as CRITICAL, ERROR, WARNING, INFO, or DEBUG
2. PATTERN ANALYSIS: Identify any concerning patterns or trends
3. RISK ASSESSMENT: Based on the logs and anomaly data, assess the deployment risk
4. ROOT CAUSE: If issues are detected, suggest potential root causes

Respond in the following JSON format:
{{
    "log_classifications": [
        {{
            "log_entry": "log text",
            "category": "CRITICAL|ERROR|WARNING|INFO|DEBUG",
            "severity_score": 0.0-1.0,
            "reasoning": "explanation"
        }}
    ],
    "patterns_detected": [
        {{
            "pattern": "description",
            "frequency": "count or frequency",
            "impact": "HIGH|MEDIUM|LOW"
        }}
    ],
    "risk_assessment": {{
        "overall_risk": "HIGH|MEDIUM|LOW",
        "confidence": 0.0-1.0,
        "key_concerns": ["concern1", "concern2"]
    }},
    "root_causes": [
        {{
            "issue": "description",
            "likelihood": "HIGH|MEDIUM|LOW",
            "evidence": ["evidence1", "evidence2"]
        }}
    ]
}}
"""
        return prompt
    
    def create_patch_readiness_prompt(self, classification_result: Dict[str, Any], anomaly_result: Dict[str, Any]) -> str:
        """Create a prompt for patch readiness assessment"""
        
        prompt = f"""You are a DevOps expert assessing patch deployment readiness based on system analysis.

ANOMALY DETECTION RESULTS:
{json.dumps(anomaly_result, indent=2, default=str)}

LOG CLASSIFICATION RESULTS:
{json.dumps(classification_result, indent=2)}

Based on this comprehensive analysis, please provide a patch deployment readiness assessment.

Consider:
1. The severity and frequency of detected issues
2. Potential impact on system stability
3. Risk of deployment vs risk of delaying
4. Recommended preventive actions
5. Deployment timing recommendations

Respond in the following JSON format:
{{
    "deployment_decision": "PROCEED|CAUTION|ABORT",
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation of the decision",
    "recommendations": [
        "specific recommendation 1",
        "specific recommendation 2"
    ],
    "preventive_actions": [
        "action to take before deployment",
        "monitoring to implement"
    ],
    "deployment_window": {{
        "recommended_time": "time recommendation",
        "conditions": ["condition1", "condition2"]
    }},
    "rollback_plan": [
        "rollback step 1",
        "rollback step 2"
    ],
    "monitoring_focus": [
        "metric to monitor closely",
        "alert to set up"
    ]
}}
"""
        return prompt
    
    def query_model(self, prompt: str) -> str:
        """Query the Qwen model with a prompt"""
        if not self.model or not self.tokenizer:
            return "{\"error\": \"Model not initialized\"}"
            
        try:
            # Prepare input
            messages = [
                {"role": "system", "content": "You are an expert system administrator and DevOps engineer."},
                {"role": "user", "content": prompt}
            ]
            
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
            
            # Generate response
            with torch.no_grad():
                generated_ids = self.model.generate(
                    model_inputs.input_ids,
                    max_new_tokens=1024,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.8,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            
            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return response.strip()
            
        except Exception as e:
            print(f"Error querying Qwen model: {e}")
            return "{\"error\": \"Model query failed\"}"
    
    def classify_logs(self, log_entries: List[str], anomaly_context: Dict[str, Any]) -> Dict[str, Any]:
        """Classify logs using Qwen LLM"""
        prompt = self.create_log_classification_prompt(log_entries, anomaly_context)
        response = self.query_model(prompt)
        
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"error": "Could not parse LLM response as JSON"}
                
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            return {"error": "Invalid JSON response from LLM"}
    
    def assess_patch_readiness(self, classification_result: Dict[str, Any], anomaly_result: Dict[str, Any]) -> PatchReadinessReport:
        """Assess patch readiness using Qwen LLM"""
        prompt = self.create_patch_readiness_prompt(classification_result, anomaly_result)
        response = self.query_model(prompt)
        
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                readiness_data = json.loads(json_str)
                
                # Create structured report
                report = PatchReadinessReport(
                    patch_time=anomaly_result.get('patch_time', datetime.now().isoformat()),
                    risk_level=anomaly_result.get('predicted_risk_level', 'UNKNOWN'),
                    confidence=anomaly_result.get('confidence', 0.0),
                    anomalies_detected=anomaly_result.get('expected_anomalies', []),
                    log_classifications=classification_result,
                    recommendations=readiness_data.get('recommendations', []),
                    preventive_actions=readiness_data.get('preventive_actions', []),
                    deployment_decision=readiness_data.get('deployment_decision', 'CAUTION'),
                    reasoning=readiness_data.get('reasoning', 'No reasoning provided')
                )
                
                return report
                
            else:
                # Fallback report
                return PatchReadinessReport(
                    patch_time=anomaly_result.get('patch_time', datetime.now().isoformat()),
                    risk_level=anomaly_result.get('predicted_risk_level', 'UNKNOWN'),
                    confidence=0.0,
                    anomalies_detected=anomaly_result.get('expected_anomalies', []),
                    log_classifications=classification_result,
                    recommendations=["Unable to generate recommendations - LLM response parsing failed"],
                    preventive_actions=["Review system manually before deployment"],
                    deployment_decision="CAUTION",
                    reasoning="LLM assessment failed, manual review required"
                )
                
        except json.JSONDecodeError as e:
            print(f"Error parsing patch readiness response: {e}")
            # Return fallback report
            return PatchReadinessReport(
                patch_time=anomaly_result.get('patch_time', datetime.now().isoformat()),
                risk_level=anomaly_result.get('predicted_risk_level', 'UNKNOWN'),
                confidence=0.0,
                anomalies_detected=anomaly_result.get('expected_anomalies', []),
                log_classifications=classification_result,
                recommendations=["LLM assessment failed - manual review required"],
                preventive_actions=["Perform thorough manual system check before deployment"],
                deployment_decision="ABORT",
                reasoning="Unable to complete automated assessment"
            )

class IntegratedPatchReadinessSystem:
    """
    Integrated system combining multi-model anomaly detection with Qwen LLM analysis
    """
    
    def __init__(self):
        self.anomaly_detector = MultiModelAnomalyDetector()
        self.llm_classifier = QwenLogClassifier()
        self.log_buffer = []
        self.max_log_buffer_size = 1000
        
    def initialize(self):
        """Initialize all components"""
        print("Initializing Integrated Patch Readiness System...")
        
        # Initialize anomaly detector
        self.anomaly_detector.initialize_models()
        
        # Initialize LLM
        if not self.llm_classifier.initialize_model():
            print("Warning: LLM initialization failed. Some features may not work.")
            
        print("System initialization complete")
    
    def add_log_entry(self, log_entry: str):
        """Add a log entry to the buffer"""
        self.log_buffer.append({
            'timestamp': datetime.now().isoformat(),
            'message': log_entry
        })
        
        # Maintain buffer size
        if len(self.log_buffer) > self.max_log_buffer_size:
            self.log_buffer = self.log_buffer[-self.max_log_buffer_size:]
    
    def fetch_recent_logs(self, count: int = 50) -> List[str]:
        """Fetch recent logs from buffer"""
        recent_logs = self.log_buffer[-count:] if len(self.log_buffer) >= count else self.log_buffer
        return [log['message'] for log in recent_logs]
    
    def run_comprehensive_assessment(self) -> PatchReadinessReport:
        """Run comprehensive patch readiness assessment"""
        print("Running comprehensive patch readiness assessment...")
        
        # Step 1: Multi-model anomaly detection
        print("1. Running multi-model anomaly detection...")
        anomaly_result = self.anomaly_detector.detect_anomalies()
        
        # Step 2: Fetch recent logs
        print("2. Fetching recent logs...")
        recent_logs = self.fetch_recent_logs(50)
        
        # Step 3: LLM log classification
        print("3. Classifying logs with Qwen LLM...")
        classification_result = self.llm_classifier.classify_logs(recent_logs, anomaly_result)
        
        # Step 4: Patch readiness assessment
        print("4. Generating patch readiness assessment...")
        readiness_report = self.llm_classifier.assess_patch_readiness(classification_result, anomaly_result)
        
        return readiness_report
    
    def generate_assessment_report(self, report: PatchReadinessReport) -> str:
        """Generate a human-readable assessment report"""
        report_text = f"""
=== PATCH READINESS ASSESSMENT REPORT ===
Generated: {report.patch_time}

DEPLOYMENT DECISION: {report.deployment_decision}
Risk Level: {report.risk_level}
Confidence: {report.confidence:.2f}

DETECTED ANOMALIES:
{chr(10).join(f"• {anomaly}" for anomaly in report.anomalies_detected) if report.anomalies_detected else "• None"}

REASONING:
{report.reasoning}

RECOMMENDATIONS:
{chr(10).join(f"• {rec}" for rec in report.recommendations)}

PREVENTIVE ACTIONS:
{chr(10).join(f"• {action}" for action in report.preventive_actions)}

LOG CLASSIFICATION SUMMARY:
"""
        
        # Add log classification summary
        if 'log_classifications' in report.log_classifications:
            classifications = report.log_classifications['log_classifications']
            severity_counts = {}
            for classification in classifications:
                category = classification.get('category', 'UNKNOWN')
                severity_counts[category] = severity_counts.get(category, 0) + 1
            
            for category, count in severity_counts.items():
                report_text += f"• {category}: {count} entries\n"
        
        report_text += f"\n=== END REPORT ==="
        
        return report_text
    
    def run_monitoring_loop(self, interval: int = 300):
        """Run continuous monitoring and assessment"""
        print("Starting continuous patch readiness monitoring...")
        
        while True:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] Running patch readiness assessment...")
                
                # Run comprehensive assessment
                report = self.run_comprehensive_assessment()
                
                # Generate and display report
                report_text = self.generate_assessment_report(report)
                print(report_text)
                
                # Publish results (could be sent to Kafka, saved to database, etc.)
                self.publish_assessment(report)
                
                # Sleep before next assessment
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\nStopping patch readiness monitoring...")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def publish_assessment(self, report: PatchReadinessReport):
        """Publish assessment results"""
        # Convert report to dictionary for JSON serialization
        report_dict = {
            'patch_time': report.patch_time,
            'risk_level': report.risk_level,
            'confidence': report.confidence,
            'anomalies_detected': report.anomalies_detected,
            'log_classifications': report.log_classifications,
            'recommendations': report.recommendations,
            'preventive_actions': report.preventive_actions,
            'deployment_decision': report.deployment_decision,
            'reasoning': report.reasoning
        }
        
        # Publish to Kafka
        self.anomaly_detector.publish_result(report_dict, topic='patch_readiness_assessments')
        
        # Could also save to database, send alerts, etc.

def main():
    """Main function to run the integrated system"""
    system = IntegratedPatchReadinessSystem()
    system.initialize()
    
    # Add some sample log entries for demo
    sample_logs = [
        "ERROR: Database connection failed - connection timeout",
        "WARNING: High memory usage detected: 85%",
        "INFO: Backup completed successfully",
        "ERROR: Authentication service unreachable",
        "CRITICAL: Disk space critical on /var/log partition"
    ]
    
    for log in sample_logs:
        system.add_log_entry(log)
    
    # Run assessment
    if len(os.sys.argv) > 1 and os.sys.argv[1] == '--once':
        # Single assessment
        report = system.run_comprehensive_assessment()
        print(system.generate_assessment_report(report))
    else:
        # Continuous monitoring
        system.run_monitoring_loop(interval=300)  # 5 minutes

if __name__ == "__main__":
    main()
