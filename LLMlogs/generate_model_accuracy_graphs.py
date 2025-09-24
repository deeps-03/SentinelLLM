#!/usr/bin/env python3
"""
Model Accuracy Visualization During Patch Operations
Shows XGBoost and Qwen performance across different patch scenarios
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Tuple
import random
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import seaborn as sns

class ModelPerformanceSimulator:
    """Simulate realistic model performance during patch scenarios"""
    
    def __init__(self):
        self.patch_scenarios = {
            "low_risk_patch": {
                "duration_minutes": 30,
                "base_accuracy": 0.95,
                "accuracy_variance": 0.02,
                "difficulty_curve": "stable",
                "color": "#2E8B57"
            },
            "medium_risk_patch": {
                "duration_minutes": 60,
                "base_accuracy": 0.88,
                "accuracy_variance": 0.05,
                "difficulty_curve": "moderate_decline",
                "color": "#FF8C00"
            },
            "high_risk_patch": {
                "duration_minutes": 90,
                "base_accuracy": 0.78,
                "accuracy_variance": 0.08,
                "difficulty_curve": "steep_decline",
                "color": "#DC143C"
            },
            "rollback_scenario": {
                "duration_minutes": 45,
                "base_accuracy": 0.65,
                "accuracy_variance": 0.12,
                "difficulty_curve": "chaotic",
                "color": "#8B0000"
            }
        }
        
        # Model characteristics
        self.model_profiles = {
            "XGBoost": {
                "strengths": ["speed", "structured_data", "stability"],
                "weaknesses": ["novel_patterns", "extreme_outliers"],
                "base_performance_factor": 1.0
            },
            "Qwen_1.5B": {
                "strengths": ["context_understanding", "novel_patterns", "complex_reasoning"],
                "weaknesses": ["speed", "resource_intensive", "consistency"],
                "base_performance_factor": 0.92  # Slightly lower base due to complexity
            },
            "Multi_Model_Ensemble": {
                "strengths": ["robustness", "comprehensive_analysis", "confidence_calibration"],
                "weaknesses": ["complexity", "latency"],
                "base_performance_factor": 1.08  # Ensemble boost
            }
        }
        
    def generate_difficulty_curve(self, scenario: str, time_points: List[datetime]) -> List[float]:
        """Generate difficulty multiplier based on patch scenario progression"""
        
        config = self.patch_scenarios[scenario]
        curve_type = config["difficulty_curve"]
        n_points = len(time_points)
        
        if curve_type == "stable":
            # Minimal variation throughout
            return [1.0 + np.random.normal(0, 0.02) for _ in range(n_points)]
            
        elif curve_type == "moderate_decline":
            # Gradual increase in difficulty towards middle, then recovery
            difficulties = []
            for i in range(n_points):
                progress = i / n_points
                # Parabolic curve peaking at 0.5 progress
                difficulty_factor = 1.0 + 0.3 * 4 * progress * (1 - progress)
                difficulties.append(difficulty_factor + np.random.normal(0, 0.03))
            return difficulties
            
        elif curve_type == "steep_decline":
            # Rapid difficulty increase, plateau, then slow recovery
            difficulties = []
            for i in range(n_points):
                progress = i / n_points
                if progress < 0.2:
                    # Rapid increase
                    difficulty_factor = 1.0 + progress * 2  # 0 to 0.4 increase
                elif progress < 0.7:
                    # High plateau
                    difficulty_factor = 1.4 + np.random.normal(0, 0.1)
                else:
                    # Slow recovery
                    recovery_progress = (progress - 0.7) / 0.3
                    difficulty_factor = 1.4 - recovery_progress * 0.3
                difficulties.append(max(0.8, difficulty_factor + np.random.normal(0, 0.05)))
            return difficulties
            
        elif curve_type == "chaotic":
            # Unpredictable difficulty spikes
            difficulties = []
            for i in range(n_points):
                # Base high difficulty with random spikes
                base_difficulty = 1.5
                spike_probability = 0.15
                if np.random.random() < spike_probability:
                    spike_factor = np.random.uniform(1.3, 2.0)
                else:
                    spike_factor = np.random.uniform(0.8, 1.2)
                difficulties.append(base_difficulty * spike_factor + np.random.normal(0, 0.1))
            return difficulties
            
        else:
            return [1.0] * n_points
    
    def simulate_model_performance(self, model_name: str, scenario: str, 
                                 time_points: List[datetime]) -> Dict[str, List[float]]:
        """Simulate model performance metrics over time"""
        
        scenario_config = self.patch_scenarios[scenario]
        model_profile = self.model_profiles[model_name]
        
        # Get difficulty curve
        difficulty_factors = self.generate_difficulty_curve(scenario, time_points)
        
        # Base performance metrics
        base_accuracy = scenario_config["base_accuracy"] * model_profile["base_performance_factor"]
        variance = scenario_config["accuracy_variance"]
        
        accuracy_scores = []
        precision_scores = []
        recall_scores = []
        f1_scores = []
        confidence_scores = []
        processing_times = []
        
        for i, difficulty in enumerate(difficulty_factors):
            # Adjust performance based on difficulty
            adjusted_accuracy = base_accuracy / difficulty
            
            # Add model-specific variations
            if model_name == "XGBoost":
                # XGBoost is more stable but struggles with high difficulty
                if difficulty > 1.3:
                    adjusted_accuracy *= 0.85
                accuracy_noise = np.random.normal(0, variance * 0.7)  # More stable
                
            elif model_name == "Qwen_1.5B":
                # Qwen is better with high difficulty but more variable
                if difficulty > 1.3:
                    adjusted_accuracy *= 1.1  # Better with complex scenarios
                accuracy_noise = np.random.normal(0, variance * 1.2)  # More variable
                
            else:  # Multi_Model_Ensemble
                # Ensemble is most robust
                if difficulty > 1.3:
                    adjusted_accuracy *= 0.95  # Slight degradation but robust
                accuracy_noise = np.random.normal(0, variance * 0.8)  # Stable
            
            # Calculate final accuracy
            final_accuracy = np.clip(adjusted_accuracy + accuracy_noise, 0.3, 1.0)
            accuracy_scores.append(final_accuracy)
            
            # Derive other metrics from accuracy (with realistic correlations)
            precision = final_accuracy + np.random.normal(0, 0.02)
            recall = final_accuracy + np.random.normal(0, 0.03)
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            precision_scores.append(np.clip(precision, 0.2, 1.0))
            recall_scores.append(np.clip(recall, 0.2, 1.0))
            f1_scores.append(np.clip(f1, 0.2, 1.0))
            
            # Confidence score (inverse of difficulty)
            confidence = (final_accuracy / difficulty) + np.random.normal(0, 0.05)
            confidence_scores.append(np.clip(confidence, 0.1, 1.0))
            
            # Processing time (model-dependent)
            if model_name == "XGBoost":
                base_time = 15  # ms
            elif model_name == "Qwen_1.5B":
                base_time = 250  # ms (much slower)
            else:  # Ensemble
                base_time = 300  # ms (slowest but comprehensive)
            
            # Processing time increases with difficulty
            proc_time = base_time * difficulty + np.random.normal(0, base_time * 0.1)
            processing_times.append(max(5, proc_time))
        
        return {
            "accuracy": accuracy_scores,
            "precision": precision_scores,
            "recall": recall_scores,
            "f1_score": f1_scores,
            "confidence": confidence_scores,
            "processing_time_ms": processing_times
        }
    
    def generate_all_performance_data(self) -> Dict[str, Dict]:
        """Generate performance data for all models and scenarios"""
        
        all_data = {}
        
        for scenario in self.patch_scenarios.keys():
            print(f"📊 Generating performance data for {scenario}...")
            
            # Create time points for this scenario
            duration = self.patch_scenarios[scenario]["duration_minutes"]
            start_time = datetime.now()
            time_points = [start_time + timedelta(minutes=i) for i in range(duration)]
            
            scenario_data = {
                "time_points": time_points,
                "models": {}
            }
            
            # Generate data for each model
            for model_name in self.model_profiles.keys():
                performance_data = self.simulate_model_performance(model_name, scenario, time_points)
                scenario_data["models"][model_name] = performance_data
                
            all_data[scenario] = scenario_data
            
        return all_data

class ModelAccuracyVisualizer:
    """Create comprehensive visualizations of model accuracy during patch operations"""
    
    def __init__(self):
        plt.style.use('seaborn-v0_8')
        self.figure_size = (16, 12)
        
    def create_model_comparison_graph(self, performance_data: Dict, 
                                    save_path: str = "model_accuracy_comparison.png"):
        """Compare all models across all scenarios"""
        
        fig, axes = plt.subplots(2, 2, figsize=self.figure_size)
        fig.suptitle('🤖 SentinelLLM - Model Performance During Patch Operations', 
                    fontsize=16, fontweight='bold', y=0.95)
        
        scenarios = list(performance_data.keys())
        
        for idx, scenario in enumerate(scenarios):
            row, col = idx // 2, idx % 2
            ax = axes[row, col]
            
            data = performance_data[scenario]
            time_points = data["time_points"]
            
            # Plot each model's accuracy
            for model_name, metrics in data["models"].items():
                accuracy = metrics["accuracy"]
                
                # Convert time to minutes from start
                minutes = [(tp - time_points[0]).total_seconds() / 60 for tp in time_points]
                
                if model_name == "XGBoost":
                    linestyle = '-'
                    marker = 'o'
                    alpha = 0.8
                elif model_name == "Qwen_1.5B":
                    linestyle = '--'
                    marker = 's'
                    alpha = 0.8
                else:  # Multi_Model_Ensemble
                    linestyle = '-.'
                    marker = '^'
                    alpha = 0.9
                
                ax.plot(minutes, accuracy, label=model_name, linestyle=linestyle,
                       marker=marker, markersize=4, linewidth=2, alpha=alpha)
            
            ax.set_title(f'{scenario.replace("_", " ").title()}', fontweight='bold')
            ax.set_xlabel('Time (minutes)')
            ax.set_ylabel('Accuracy Score')
            ax.set_ylim(0.3, 1.0)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='lower right', fontsize=9)
            
        plt.tight_layout()
        plt.subplots_adjust(top=0.92)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Model comparison graph saved to: {save_path}")
        
        return fig
    
    def create_performance_metrics_dashboard(self, performance_data: Dict,
                                           save_path: str = "performance_dashboard.png"):
        """Create comprehensive dashboard with all performance metrics"""
        
        fig, axes = plt.subplots(3, 2, figsize=(16, 14))
        fig.suptitle('📈 SentinelLLM - Comprehensive Model Performance Dashboard', 
                    fontsize=16, fontweight='bold', y=0.96)
        
        # Colors for different models
        model_colors = {
            "XGBoost": "#2E8B57",
            "Qwen_1.5B": "#FF6347", 
            "Multi_Model_Ensemble": "#4169E1"
        }
        
        metrics_to_plot = ["accuracy", "precision", "recall", "f1_score", "confidence", "processing_time_ms"]
        metric_titles = ["Accuracy", "Precision", "Recall", "F1 Score", "Confidence", "Processing Time (ms)"]
        
        for metric_idx, (metric, title) in enumerate(zip(metrics_to_plot, metric_titles)):
            row, col = metric_idx // 2, metric_idx % 2
            ax = axes[row, col]
            
            # Aggregate data across all scenarios for each model
            for model_name in ["XGBoost", "Qwen_1.5B", "Multi_Model_Ensemble"]:
                all_values = []
                
                for scenario_data in performance_data.values():
                    if model_name in scenario_data["models"]:
                        values = scenario_data["models"][model_name][metric]
                        all_values.extend(values)
                
                if all_values:
                    if metric == "processing_time_ms":
                        # Log scale for processing time
                        ax.hist(all_values, bins=20, alpha=0.6, label=model_name, 
                               color=model_colors[model_name], density=True)
                        ax.set_yscale('log')
                    else:
                        # Regular scale for other metrics
                        ax.hist(all_values, bins=20, alpha=0.6, label=model_name,
                               color=model_colors[model_name], density=True)
            
            ax.set_title(title, fontweight='bold')
            ax.set_xlabel(title if metric != "processing_time_ms" else "Time (ms)")
            ax.set_ylabel('Density')
            ax.grid(True, alpha=0.3)
            ax.legend()
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.92)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Performance dashboard saved to: {save_path}")
        
        return fig
    
    def create_scenario_difficulty_analysis(self, performance_data: Dict,
                                          save_path: str = "scenario_difficulty.png"):
        """Analyze how model performance varies with scenario difficulty"""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=self.figure_size)
        fig.suptitle('🎯 Scenario Difficulty Impact on Model Performance', 
                    fontsize=16, fontweight='bold', y=0.95)
        
        # Calculate average metrics per scenario per model
        scenario_names = []
        model_data = {model: {"accuracy": [], "processing_time": [], "confidence": []} 
                     for model in ["XGBoost", "Qwen_1.5B", "Multi_Model_Ensemble"]}
        
        for scenario, data in performance_data.items():
            scenario_names.append(scenario.replace("_", " ").title())
            
            for model_name in ["XGBoost", "Qwen_1.5B", "Multi_Model_Ensemble"]:
                if model_name in data["models"]:
                    metrics = data["models"][model_name]
                    model_data[model_name]["accuracy"].append(np.mean(metrics["accuracy"]))
                    model_data[model_name]["processing_time"].append(np.mean(metrics["processing_time_ms"]))
                    model_data[model_name]["confidence"].append(np.mean(metrics["confidence"]))
        
        x = np.arange(len(scenario_names))
        width = 0.25
        
        # Average accuracy by scenario
        for i, (model, color) in enumerate([("XGBoost", "#2E8B57"), ("Qwen_1.5B", "#FF6347"), 
                                          ("Multi_Model_Ensemble", "#4169E1")]):
            ax1.bar(x + i*width, model_data[model]["accuracy"], width, 
                   label=model, color=color, alpha=0.8)
        
        ax1.set_title('Average Accuracy by Scenario', fontweight='bold')
        ax1.set_xlabel('Scenario')
        ax1.set_ylabel('Accuracy')
        ax1.set_xticks(x + width)
        ax1.set_xticklabels(scenario_names, rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Processing time by scenario
        for i, (model, color) in enumerate([("XGBoost", "#2E8B57"), ("Qwen_1.5B", "#FF6347"), 
                                          ("Multi_Model_Ensemble", "#4169E1")]):
            ax2.bar(x + i*width, model_data[model]["processing_time"], width,
                   label=model, color=color, alpha=0.8)
        
        ax2.set_title('Average Processing Time by Scenario', fontweight='bold')
        ax2.set_xlabel('Scenario')
        ax2.set_ylabel('Processing Time (ms)')
        ax2.set_xticks(x + width)
        ax2.set_xticklabels(scenario_names, rotation=45, ha='right')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Confidence by scenario
        for i, (model, color) in enumerate([("XGBoost", "#2E8B57"), ("Qwen_1.5B", "#FF6347"), 
                                          ("Multi_Model_Ensemble", "#4169E1")]):
            ax3.bar(x + i*width, model_data[model]["confidence"], width,
                   label=model, color=color, alpha=0.8)
        
        ax3.set_title('Average Confidence by Scenario', fontweight='bold')
        ax3.set_xlabel('Scenario')
        ax3.set_ylabel('Confidence Score')
        ax3.set_xticks(x + width)
        ax3.set_xticklabels(scenario_names, rotation=45, ha='right')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Accuracy vs Processing Time scatter plot
        for model, color in [("XGBoost", "#2E8B57"), ("Qwen_1.5B", "#FF6347"), 
                            ("Multi_Model_Ensemble", "#4169E1")]:
            ax4.scatter(model_data[model]["processing_time"], model_data[model]["accuracy"],
                       label=model, color=color, s=100, alpha=0.8)
        
        ax4.set_title('Accuracy vs Processing Time Trade-off', fontweight='bold')
        ax4.set_xlabel('Processing Time (ms)')
        ax4.set_ylabel('Accuracy')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.92)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Scenario difficulty analysis saved to: {save_path}")
        
        return fig

def main():
    """Main function to generate model accuracy visualizations"""
    
    print("🤖 SentinelLLM - Model Accuracy Visualization Generator")
    print("=" * 55)
    
    # Generate performance data
    simulator = ModelPerformanceSimulator()
    performance_data = simulator.generate_all_performance_data()
    
    # Create visualizations
    visualizer = ModelAccuracyVisualizer()
    
    print("\n📈 Creating model performance visualizations...")
    
    # Create output directory
    os.makedirs("graphs", exist_ok=True)
    
    # Generate all graphs
    visualizer.create_model_comparison_graph(performance_data, "graphs/model_accuracy_comparison.png")
    visualizer.create_performance_metrics_dashboard(performance_data, "graphs/performance_dashboard.png")
    visualizer.create_scenario_difficulty_analysis(performance_data, "graphs/scenario_difficulty.png")
    
    # Save performance data as JSON
    json_data = {}
    for scenario, data in performance_data.items():
        json_data[scenario] = {
            "models": {}
        }
        for model, metrics in data["models"].items():
            # Calculate summary statistics
            json_data[scenario]["models"][model] = {
                "avg_accuracy": float(np.mean(metrics["accuracy"])),
                "min_accuracy": float(np.min(metrics["accuracy"])),
                "max_accuracy": float(np.max(metrics["accuracy"])),
                "avg_processing_time": float(np.mean(metrics["processing_time_ms"])),
                "avg_confidence": float(np.mean(metrics["confidence"])),
                "std_accuracy": float(np.std(metrics["accuracy"]))
            }
    
    with open("graphs/model_performance_data.json", "w") as f:
        json.dump(json_data, f, indent=2)
    
    print("\n✅ Model accuracy visualization completed!")
    print("📁 Files created:")
    print("   • graphs/model_accuracy_comparison.png - Model comparison across scenarios")
    print("   • graphs/performance_dashboard.png - Comprehensive metrics dashboard")
    print("   • graphs/scenario_difficulty.png - Scenario difficulty analysis")
    print("   • graphs/model_performance_data.json - Performance summary data")
    
    # Print performance summary
    print("\n🎯 Model Performance Summary:")
    print("-" * 80)
    print(f"{'Scenario':<20} | {'Model':<20} | {'Avg Accuracy':<12} | {'Avg Time (ms)':<12}")
    print("-" * 80)
    
    for scenario, data in json_data.items():
        for model, stats in data["models"].items():
            print(f"{scenario.replace('_', ' '):<20} | {model:<20} | "
                  f"{stats['avg_accuracy']:>10.3f} | {stats['avg_processing_time']:>10.1f}")

if __name__ == "__main__":
    main()