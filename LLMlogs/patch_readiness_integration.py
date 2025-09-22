#!/usr/bin/env python3
"""
Integration example: Multi-Model Patch Analysis + Qwen for Log Classification
Shows how to combine ML patch analysis with Qwen LLM for complete patch readiness assessment
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from patch_analyzer import PatchAnalyzer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatchReadinessAssessment:
    """
    Complete patch readiness system that combines:
    1. ML models for numerical metrics analysis (patch_analyzer.py)
    2. Qwen LLM for log classification and suggestions (your existing system)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize ML patch analyzer
        self.patch_analyzer = PatchAnalyzer(self.config.get("ml_config", {}))
        self.analyzer_ready = False
        
        # Qwen integration would go here (using your existing implementation)
        # self.qwen_model = QwenLogClassifier()
        
    def prepare_system(self, historical_metrics: List[Dict[str, Any]]) -> bool:
        """Prepare the ML models with historical data"""
        logger.info("Preparing patch analysis system...")
        
        success = self.patch_analyzer.prepare_models(historical_metrics)
        if success:
            self.analyzer_ready = True
            logger.info("✅ Patch analyzer ready")
        else:
            logger.error("❌ Failed to prepare patch analyzer")
        
        return success
    
    def analyze_patch_readiness(self, 
                              current_metrics: Dict[str, Any],
                              recent_logs: List[str] = None) -> Dict[str, Any]:
        """
        Complete patch readiness analysis combining ML metrics and LLM log analysis
        
        Args:
            current_metrics: System metrics (CPU, memory, response time, etc.)
            recent_logs: Recent log entries for Qwen analysis
            
        Returns:
            Complete assessment with risk level, confidence, and recommendations
        """
        
        if not self.analyzer_ready:
            return {
                "error": "System not ready. Call prepare_system() first.",
                "risk_level": "UNKNOWN",
                "confidence": 0.0
            }
        
        # 1. ML Analysis of Metrics
        ml_analysis = self.patch_analyzer.analyze_patch_metrics(current_metrics)
        
        # 2. Log Analysis with Qwen (placeholder - you'll integrate your Qwen model here)
        log_analysis = self._analyze_logs_with_qwen(recent_logs or [])
        
        # 3. Combine ML and LLM insights
        combined_assessment = self._combine_assessments(ml_analysis, log_analysis)
        
        return combined_assessment
    
    def _analyze_logs_with_qwen(self, logs: List[str]) -> Dict[str, Any]:
        """
        Placeholder for Qwen log analysis
        Replace this with your actual Qwen implementation
        """
        
        # This is where you'd integrate your existing Qwen model
        # Example structure of what Qwen analysis might return:
        
        if not logs:
            return {
                "log_risk": "LOW",
                "log_confidence": 0.5,
                "detected_issues": [],
                "log_summary": "No logs provided for analysis"
            }
        
        # Simulate Qwen analysis (replace with actual implementation)
        detected_issues = []
        log_risk = "LOW"
        log_confidence = 0.6
        
        # Simple keyword-based simulation (replace with Qwen)
        error_keywords = ["error", "exception", "failed", "timeout", "critical"]
        warning_keywords = ["warning", "slow", "retry", "deprecated"]
        
        error_count = 0
        warning_count = 0
        
        for log_entry in logs:
            log_lower = log_entry.lower()
            if any(keyword in log_lower for keyword in error_keywords):
                error_count += 1
            elif any(keyword in log_lower for keyword in warning_keywords):
                warning_count += 1
        
        if error_count > 5:
            log_risk = "HIGH"
            log_confidence = 0.8
            detected_issues.append(f"High error frequency detected ({error_count} errors)")
        elif error_count > 2 or warning_count > 10:
            log_risk = "MEDIUM"
            log_confidence = 0.7
            detected_issues.append(f"Moderate issues detected ({error_count} errors, {warning_count} warnings)")
        
        return {
            "log_risk": log_risk,
            "log_confidence": log_confidence,
            "detected_issues": detected_issues,
            "log_summary": f"Analyzed {len(logs)} log entries: {error_count} errors, {warning_count} warnings",
            "error_count": error_count,
            "warning_count": warning_count
        }
    
    def _combine_assessments(self, 
                           ml_analysis: Dict[str, Any], 
                           log_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Combine ML metrics analysis with Qwen log analysis"""
        
        # Risk level mapping
        risk_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        
        # Get risk scores
        ml_risk = risk_levels.get(ml_analysis.get("predicted_risk_level", "LOW"), 1)
        log_risk = risk_levels.get(log_analysis.get("log_risk", "LOW"), 1)
        
        # Weighted combination (you can adjust these weights)
        ml_weight = 0.6  # ML metrics slightly more weight
        log_weight = 0.4  # Log analysis weight
        
        combined_risk_score = (ml_risk * ml_weight) + (log_risk * log_weight)
        
        # Convert back to risk level
        if combined_risk_score >= 2.5:
            final_risk = "HIGH"
        elif combined_risk_score >= 1.5:
            final_risk = "MEDIUM"
        else:
            final_risk = "LOW"
        
        # Combine confidences
        ml_confidence = ml_analysis.get("confidence", 0.5)
        log_confidence = log_analysis.get("log_confidence", 0.5)
        combined_confidence = (ml_confidence * ml_weight) + (log_confidence * log_weight)
        
        # Gather all detected issues
        all_issues = []
        all_issues.extend(ml_analysis.get("expected_anomalies", []))
        all_issues.extend(log_analysis.get("detected_issues", []))
        
        # Generate recommendations based on combined analysis
        recommendations = self._generate_recommendations(ml_analysis, log_analysis, final_risk)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "final_risk_level": final_risk,
            "overall_confidence": round(combined_confidence, 3),
            "ml_analysis": {
                "risk": ml_analysis.get("predicted_risk_level", "LOW"),
                "confidence": ml_analysis.get("confidence", 0.5),
                "anomalies": ml_analysis.get("expected_anomalies", [])
            },
            "log_analysis": {
                "risk": log_analysis.get("log_risk", "LOW"),
                "confidence": log_analysis.get("log_confidence", 0.5),
                "issues": log_analysis.get("detected_issues", []),
                "summary": log_analysis.get("log_summary", "")
            },
            "combined_issues": all_issues,
            "recommendations": recommendations,
            "patch_readiness": self._assess_patch_readiness(final_risk, combined_confidence)
        }
    
    def _generate_recommendations(self, 
                                ml_analysis: Dict[str, Any], 
                                log_analysis: Dict[str, Any],
                                final_risk: str) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        
        recommendations = []
        
        # ML-based recommendations
        ml_anomalies = ml_analysis.get("expected_anomalies", [])
        for anomaly in ml_anomalies:
            if "CPU" in anomaly or "cpu" in anomaly.lower():
                recommendations.append("🔧 Monitor CPU usage closely during patch deployment")
                recommendations.append("⚡ Consider scaling resources before patch")
            elif "memory" in anomaly.lower():
                recommendations.append("💾 Check memory leaks and optimize before patch")
                recommendations.append("📊 Monitor memory usage patterns post-patch")
            elif "response time" in anomaly.lower() or "latency" in anomaly.lower():
                recommendations.append("🚀 Investigate performance bottlenecks")
                recommendations.append("🔍 Review database query performance")
            elif "error" in anomaly.lower():
                recommendations.append("🐛 Address existing error patterns before patch")
        
        # Log-based recommendations
        log_issues = log_analysis.get("detected_issues", [])
        error_count = log_analysis.get("error_count", 0)
        warning_count = log_analysis.get("warning_count", 0)
        
        if error_count > 5:
            recommendations.append("🚨 High error rate detected - investigate root causes")
            recommendations.append("⏰ Consider delaying patch until errors are resolved")
        elif error_count > 0:
            recommendations.append("⚠️ Monitor error logs during patch deployment")
        
        if warning_count > 10:
            recommendations.append("📋 Review warning patterns for potential issues")
        
        # Risk-based recommendations
        if final_risk == "HIGH":
            recommendations.append("🛑 HIGH RISK: Consider postponing patch deployment")
            recommendations.append("🔄 Ensure rollback procedures are ready")
            recommendations.append("👥 Have additional support staff available")
        elif final_risk == "MEDIUM":
            recommendations.append("⚠️ MEDIUM RISK: Proceed with caution")
            recommendations.append("📊 Increase monitoring during patch")
            recommendations.append("🎯 Deploy during low-traffic hours")
        else:
            recommendations.append("✅ LOW RISK: Patch deployment can proceed normally")
            recommendations.append("📈 Maintain standard monitoring procedures")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _assess_patch_readiness(self, risk_level: str, confidence: float) -> Dict[str, Any]:
        """Assess overall patch readiness"""
        
        if risk_level == "HIGH":
            readiness = "NOT READY"
            action = "DELAY PATCH"
            color = "🔴"
        elif risk_level == "MEDIUM":
            if confidence > 0.7:
                readiness = "PROCEED WITH CAUTION"
                action = "DEPLOY WITH MONITORING"
                color = "🟡"
            else:
                readiness = "NEEDS REVIEW"
                action = "MANUAL REVIEW REQUIRED"
                color = "🟠"
        else:
            readiness = "READY"
            action = "PROCEED NORMALLY"
            color = "🟢"
        
        return {
            "status": readiness,
            "recommended_action": action,
            "indicator": color,
            "confidence_level": "HIGH" if confidence > 0.8 else "MEDIUM" if confidence > 0.6 else "LOW"
        }


def demo_integration():
    """Demonstrate the integrated patch readiness assessment"""
    
    print("🚀 PATCH READINESS ASSESSMENT DEMO")
    print("="*50)
    
    # Initialize system
    config = {
        "ml_config": {
            "sliding_window_size": 50,
            "ema_alpha": 0.3,
            "threshold_std": 2.0,
            "model_weights": {
                "sliding_window": 0.35,
                "prophet": 0.35,
                "isolation_forest": 0.30
            }
        }
    }
    
    assessment_system = PatchReadinessAssessment(config)
    
    # Generate sample historical data
    print("📊 Preparing system with historical data...")
    historical_data = []
    base_time = datetime.now() - timedelta(days=7)
    
    for i in range(168):  # 7 days of hourly data
        timestamp = base_time + timedelta(hours=i)
        historical_data.append({
            "timestamp": timestamp,
            "metric_value": 50 + np.random.normal(0, 15),
            "cpu_usage": 50 + np.random.normal(0, 15),
            "memory_usage": 60 + np.random.normal(0, 12),
            "response_time": 200 + np.random.normal(0, 40),
            "error_rate": max(0, np.random.normal(1, 1.5))
        })
    
    success = assessment_system.prepare_system(historical_data)
    if not success:
        print("❌ Failed to prepare system")
        return
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Normal Conditions",
            "metrics": {
                "timestamp": datetime.now(),
                "metric_value": 55.2,
                "cpu_usage": 55.2,
                "memory_usage": 62.1,
                "response_time": 205.3,
                "error_rate": 0.9
            },
            "logs": [
                "2024-01-15 10:30:00 INFO Application started successfully",
                "2024-01-15 10:31:00 INFO Processing request batch",
                "2024-01-15 10:32:00 INFO Request completed successfully"
            ]
        },
        {
            "name": "High Resource Usage + Errors",
            "metrics": {
                "timestamp": datetime.now(),
                "metric_value": 89.7,
                "cpu_usage": 89.7,
                "memory_usage": 91.2,
                "response_time": 456.8,
                "error_rate": 5.2
            },
            "logs": [
                "2024-01-15 10:30:00 ERROR Database connection timeout",
                "2024-01-15 10:30:05 ERROR Failed to process request: OutOfMemoryException",
                "2024-01-15 10:30:10 ERROR Critical: Service unavailable",
                "2024-01-15 10:30:15 WARNING High CPU usage detected",
                "2024-01-15 10:30:20 ERROR Request failed with timeout",
                "2024-01-15 10:30:25 ERROR Authentication service error"
            ]
        }
    ]
    
    # Run assessments
    for scenario in test_scenarios:
        print(f"\n{'='*50}")
        print(f"SCENARIO: {scenario['name']}")
        print(f"{'='*50}")
        
        result = assessment_system.analyze_patch_readiness(
            scenario["metrics"], 
            scenario["logs"]
        )
        
        # Display results
        readiness = result["patch_readiness"]
        print(f"{readiness['indicator']} PATCH READINESS: {readiness['status']}")
        print(f"📊 RISK LEVEL: {result['final_risk_level']}")
        print(f"🎯 CONFIDENCE: {result['overall_confidence']:.3f} ({readiness['confidence_level']})")
        print(f"⚡ RECOMMENDED ACTION: {readiness['recommended_action']}")
        
        print(f"\n📈 ML ANALYSIS:")
        print(f"   Risk: {result['ml_analysis']['risk']}")
        print(f"   Anomalies: {len(result['ml_analysis']['anomalies'])}")
        if result['ml_analysis']['anomalies']:
            for anomaly in result['ml_analysis']['anomalies'][:3]:  # Show first 3
                print(f"   • {anomaly}")
        
        print(f"\n📝 LOG ANALYSIS:")
        print(f"   Risk: {result['log_analysis']['risk']}")
        print(f"   Summary: {result['log_analysis']['summary']}")
        if result['log_analysis']['issues']:
            for issue in result['log_analysis']['issues']:
                print(f"   • {issue}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(result['recommendations'][:5], 1):  # Show first 5
            print(f"   {i}. {rec}")
        
        if len(result['recommendations']) > 5:
            print(f"   ... and {len(result['recommendations'])-5} more recommendations")
    
    print(f"\n{'='*50}")
    print("✅ INTEGRATION DEMO COMPLETED")
    print("="*50)


if __name__ == "__main__":
    import numpy as np  # Import numpy for demo
    demo_integration()
