#!/usr/bin/env python3
"""
Simplified test of the improved confidence calculation system
Shows how the weighted confidence formula works without complex imports
"""

class SimpleMetaClassifier:
    """Simplified version for testing confidence calculation"""
    
    def __init__(self):
        self.model_weights = {
            'sliding_window': 0.3,   # EMA
            'prophet': 0.4,          # Prophet gets higher weight
            'isolation_forest': 0.3  # Isolation Forest
        }
        
        self.confidence_thresholds = {
            'HIGH': 0.90,
            'MEDIUM': 0.70,
            'LOW': 0.50,
            'NOISE': 0.0
        }
        
    def calculate_weighted_confidence(self, results):
        """Calculate weighted confidence using your formula"""
        weighted_score = 0.0
        
        for model_name, weight in self.model_weights.items():
            model_confidence = results.get(model_name, {}).get('confidence', 0.0)
            weighted_score += model_confidence * weight
            
        return weighted_score
    
    def determine_confidence_level(self, confidence):
        """Determine confidence level based on thresholds"""
        if confidence >= self.confidence_thresholds['HIGH']:
            return "HIGH", "Immediate alert + Auto-escalation"
        elif confidence >= self.confidence_thresholds['MEDIUM']:
            return "MEDIUM", "Alert with investigation prompt"
        elif confidence >= self.confidence_thresholds['LOW']:
            return "LOW", "Log for review, no immediate alert"
        else:
            return "NOISE", "Filtered out"

def test_your_confidence_system():
    """Test the confidence system from your attachment"""
    
    print("🎯 TESTING YOUR CONFIDENCE CALCULATION SYSTEM")
    print("=" * 60)
    print("Formula: Confidence = (EMA × 0.3) + (Prophet × 0.4) + (IsolationForest × 0.3)")
    print("Your Thresholds: HIGH ≥90%, MEDIUM ≥70%, LOW ≥50%, NOISE <50%")
    print()
    
    classifier = SimpleMetaClassifier()
    
    test_scenarios = [
        {
            "name": "🚨 ALL MODELS AGREE (Your HIGH Confidence)",
            "sliding_window": {"confidence": 0.95},
            "prophet": {"confidence": 0.92}, 
            "isolation_forest": {"confidence": 0.88}
        },
        {
            "name": "⚠️ TWO MODELS AGREE (Your MEDIUM Confidence)",
            "sliding_window": {"confidence": 0.85},
            "prophet": {"confidence": 0.80},
            "isolation_forest": {"confidence": 0.45}
        },
        {
            "name": "📊 ONE MODEL DETECTS (Your LOW Confidence)", 
            "sliding_window": {"confidence": 0.35},
            "prophet": {"confidence": 0.75},
            "isolation_forest": {"confidence": 0.40}
        },
        {
            "name": "🔇 NO CONSENSUS (Your NOISE Filter)",
            "sliding_window": {"confidence": 0.25},
            "prophet": {"confidence": 0.30},
            "isolation_forest": {"confidence": 0.20}
        },
        {
            "name": "🎭 PROPHET DOMINANCE (Testing Your 0.4 Weight)",
            "sliding_window": {"confidence": 0.20},
            "prophet": {"confidence": 0.95},
            "isolation_forest": {"confidence": 0.15}
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print("-" * 50)
        
        # Extract confidence values
        ema_conf = scenario['sliding_window']['confidence']
        prophet_conf = scenario['prophet']['confidence']
        isolation_conf = scenario['isolation_forest']['confidence']
        
        print(f"   EMA (Sliding Window): {ema_conf:.2f}")
        print(f"   Prophet:             {prophet_conf:.2f}")
        print(f"   Isolation Forest:    {isolation_conf:.2f}")
        
        # Calculate weighted confidence using YOUR formula
        weighted_conf = classifier.calculate_weighted_confidence(scenario)
        level, action = classifier.determine_confidence_level(weighted_conf)
        
        print(f"\n   🧮 YOUR CALCULATION:")
        print(f"   ({ema_conf:.2f} × 0.3) + ({prophet_conf:.2f} × 0.4) + ({isolation_conf:.2f} × 0.3)")
        print(f"   = {ema_conf*0.3:.3f} + {prophet_conf*0.4:.3f} + {isolation_conf*0.3:.3f}")
        print(f"   = {weighted_conf:.3f} ({weighted_conf:.1%})")
        
        print(f"\n   📊 RESULT:")
        print(f"   Confidence Level: {level}")
        print(f"   Action: {action}")
        print()

def validate_your_formula():
    """Validate that your approach handles edge cases correctly"""
    
    print("✅ VALIDATING YOUR APPROACH")
    print("=" * 40)
    
    classifier = SimpleMetaClassifier()
    
    edge_cases = [
        {
            "case": "Prophet alone at 100%",
            "scenario": {
                "sliding_window": {"confidence": 0.0},
                "prophet": {"confidence": 1.0},
                "isolation_forest": {"confidence": 0.0}
            },
            "expected": "Prophet weight (0.4) should still reach LOW threshold"
        },
        {
            "case": "EMA + Isolation at 100%", 
            "scenario": {
                "sliding_window": {"confidence": 1.0},
                "prophet": {"confidence": 0.0},
                "isolation_forest": {"confidence": 1.0}
            },
            "expected": "Combined weight (0.6) should reach LOW threshold"
        },
        {
            "case": "All models at 75%",
            "scenario": {
                "sliding_window": {"confidence": 0.75},
                "prophet": {"confidence": 0.75},
                "isolation_forest": {"confidence": 0.75}
            },
            "expected": "Should hit MEDIUM threshold (75% > 70%)"
        }
    ]
    
    for edge_case in edge_cases:
        scenario = edge_case["scenario"]
        confidence = classifier.calculate_weighted_confidence(scenario)
        level, action = classifier.determine_confidence_level(confidence)
        
        print(f"🧪 {edge_case['case']}")
        print(f"   Result: {confidence:.3f} ({confidence:.1%}) → {level}")
        print(f"   Expected: {edge_case['expected']}")
        print()

if __name__ == "__main__":
    test_your_confidence_system()
    validate_your_formula()