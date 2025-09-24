#!/usr/bin/env python3
"""
Time-Based Spike Pattern Generator with Real Graphs
Shows how spikes occur during different patch scenarios over time
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import json
import os
import time
import random
from typing import List, Dict, Tuple

class SpikePatternGenerator:
    """Generate realistic spike patterns for different patch scenarios"""
    
    def __init__(self):
        self.scenarios = {
            "normal_operation": {
                "base_load": 20,
                "spike_frequency": 0.02,
                "spike_intensity": 1.5,
                "duration_hours": 2,
                "color": "#2E8B57"  # Sea Green
            },
            "patch_deployment": {
                "base_load": 40, 
                "spike_frequency": 0.15,
                "spike_intensity": 3.5,
                "duration_hours": 1.5,
                "color": "#FF6347"  # Tomato Red
            },
            "system_stress": {
                "base_load": 70,
                "spike_frequency": 0.25,
                "spike_intensity": 2.8,
                "duration_hours": 1,
                "color": "#DC143C"  # Crimson
            },
            "recovery_phase": {
                "base_load": 35,
                "spike_frequency": 0.08,
                "spike_intensity": 2.0,
                "duration_hours": 2.5,
                "color": "#4169E1"  # Royal Blue
            }
        }
        
    def generate_time_series_data(self, scenario: str, points_per_hour: int = 60) -> Tuple[List[datetime], List[float], List[bool]]:
        """Generate time series data with realistic spike patterns"""
        
        config = self.scenarios[scenario]
        total_points = int(config["duration_hours"] * points_per_hour)
        
        # Generate time points
        start_time = datetime.now()
        time_points = [start_time + timedelta(minutes=i/points_per_hour*60) for i in range(total_points)]
        
        # Generate base load with time-based variations
        base_values = []
        spike_markers = []
        
        for i in range(total_points):
            # Time-based variation (sine wave for daily patterns)
            time_factor = np.sin(2 * np.pi * i / (points_per_hour * 24)) * 0.3
            
            # Patch-specific progression patterns
            progress = i / total_points
            
            if scenario == "patch_deployment":
                # Stress increases towards middle, then decreases
                stress_curve = 4 * progress * (1 - progress)  # Parabolic curve
                base_load = config["base_load"] + stress_curve * 30
            elif scenario == "system_stress":
                # High constant stress with gradual increase
                stress_curve = progress * 0.5
                base_load = config["base_load"] + stress_curve * 20
            elif scenario == "recovery_phase":
                # Exponential decay pattern
                recovery_factor = np.exp(-progress * 3)
                base_load = config["base_load"] * (0.4 + 0.6 * recovery_factor)
            else:  # normal_operation
                base_load = config["base_load"]
            
            # Add time-based variation and noise
            value = base_load * (1 + time_factor) + np.random.normal(0, 5)
            
            # Determine if this point should have a spike
            is_spike = np.random.random() < config["spike_frequency"]
            
            if is_spike:
                spike_multiplier = config["spike_intensity"] * np.random.uniform(0.7, 1.3)
                value *= spike_multiplier
                
            base_values.append(max(0, min(100, value)))
            spike_markers.append(is_spike)
            
        return time_points, base_values, spike_markers
    
    def generate_all_scenarios_data(self) -> Dict[str, Dict]:
        """Generate data for all scenarios"""
        
        all_data = {}
        
        for scenario_name in self.scenarios.keys():
            print(f"📊 Generating data for {scenario_name}...")
            
            time_points, values, spikes = self.generate_time_series_data(scenario_name)
            
            all_data[scenario_name] = {
                "time_points": time_points,
                "values": values,
                "spikes": spikes,
                "config": self.scenarios[scenario_name],
                "statistics": {
                    "avg_value": np.mean(values),
                    "max_value": np.max(values),
                    "spike_count": sum(spikes),
                    "spike_percentage": (sum(spikes) / len(spikes)) * 100
                }
            }
            
        return all_data

class GraphVisualizer:
    """Create comprehensive graphs showing spike patterns and trends"""
    
    def __init__(self):
        plt.style.use('seaborn-v0_8')  # Modern style
        self.figure_size = (15, 12)
        
    def create_spike_timeline_graph(self, scenario_data: Dict[str, Dict], save_path: str = "spike_timeline.png"):
        """Create timeline graph showing all scenarios with spike patterns"""
        
        fig, axes = plt.subplots(2, 2, figsize=self.figure_size)
        fig.suptitle('🎯 SentinelLLM - Spike Patterns During Patch Scenarios', 
                    fontsize=16, fontweight='bold', y=0.95)
        
        scenarios = list(scenario_data.keys())
        
        for idx, (scenario_name, data) in enumerate(scenario_data.items()):
            row, col = idx // 2, idx % 2
            ax = axes[row, col]
            
            time_points = data["time_points"]
            values = data["values"]
            spikes = data["spikes"]
            config = data["config"]
            
            # Plot base line
            ax.plot(time_points, values, color=config["color"], linewidth=2, 
                   label=f'{scenario_name.replace("_", " ").title()}', alpha=0.7)
            
            # Highlight spikes
            spike_times = [time_points[i] for i, is_spike in enumerate(spikes) if is_spike]
            spike_values = [values[i] for i, is_spike in enumerate(spikes) if is_spike]
            
            if spike_times:
                ax.scatter(spike_times, spike_values, color='red', s=30, alpha=0.8, 
                          marker='^', label='Spikes', zorder=5)
            
            # Fill area under curve
            ax.fill_between(time_points, values, alpha=0.3, color=config["color"])
            
            # Customize subplot
            ax.set_title(f'{scenario_name.replace("_", " ").title()}\n'
                        f'Avg: {data["statistics"]["avg_value"]:.1f}% | '
                        f'Spikes: {data["statistics"]["spike_count"]} '
                        f'({data["statistics"]["spike_percentage"]:.1f}%)',
                        fontsize=11, fontweight='bold')
            
            ax.set_ylabel('System Load (%)', fontweight='bold')
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)
            
            # Format time axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
            
            # Rotate time labels
            for label in ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')
            
        plt.tight_layout()
        plt.subplots_adjust(top=0.92, hspace=0.4, wspace=0.3)
        
        # Save the graph
        plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print(f"📊 Spike timeline graph saved to: {save_path}")
        
        return fig
    
    def create_comparative_analysis_graph(self, scenario_data: Dict[str, Dict], 
                                        save_path: str = "comparative_analysis.png"):
        """Create comparative analysis showing all scenarios on one graph"""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Top graph: All scenarios overlaid
        ax1.set_title('🔥 System Load Comparison Across Patch Scenarios', 
                     fontsize=14, fontweight='bold', pad=20)
        
        for scenario_name, data in scenario_data.items():
            time_points = data["time_points"]
            values = data["values"]
            config = data["config"]
            
            # Normalize time to start from 0 minutes
            relative_times = [(tp - time_points[0]).total_seconds() / 60 for tp in time_points]
            
            ax1.plot(relative_times, values, color=config["color"], linewidth=3, 
                    label=scenario_name.replace("_", " ").title(), alpha=0.8)
            
        ax1.set_xlabel('Time (minutes)', fontweight='bold')
        ax1.set_ylabel('System Load (%)', fontweight='bold')
        ax1.set_ylim(0, 100)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)
        
        # Bottom graph: Spike frequency comparison
        ax2.set_title('📈 Spike Frequency Analysis', fontsize=14, fontweight='bold', pad=20)
        
        scenario_names = [name.replace("_", " ").title() for name in scenario_data.keys()]
        spike_percentages = [data["statistics"]["spike_percentage"] for data in scenario_data.values()]
        colors = [data["config"]["color"] for data in scenario_data.values()]
        
        bars = ax2.bar(scenario_names, spike_percentages, color=colors, alpha=0.7, 
                      edgecolor='black', linewidth=1)
        
        # Add value labels on bars
        for bar, percentage in zip(bars, spike_percentages):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{percentage:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        ax2.set_ylabel('Spike Frequency (%)', fontweight='bold')
        ax2.set_ylim(0, max(spike_percentages) * 1.2)
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Rotate x-axis labels
        for label in ax2.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print(f"📊 Comparative analysis graph saved to: {save_path}")
        
        return fig
    
    def create_statistical_summary_graph(self, scenario_data: Dict[str, Dict],
                                       save_path: str = "statistical_summary.png"):
        """Create statistical summary with box plots and distribution analysis"""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=self.figure_size)
        fig.suptitle('📊 SentinelLLM - Statistical Analysis of System Behavior', 
                    fontsize=16, fontweight='bold', y=0.95)
        
        # Prepare data for box plots
        scenario_names = list(scenario_data.keys())
        all_values = [data["values"] for data in scenario_data.values()]
        colors = [data["config"]["color"] for data in scenario_data.values()]
        
        # Box plot of system loads
        bp1 = ax1.boxplot(all_values, labels=[name.replace("_", " ").title() for name in scenario_names],
                         patch_artist=True, notch=True)
        
        for patch, color in zip(bp1['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax1.set_title('System Load Distribution', fontweight='bold')
        ax1.set_ylabel('System Load (%)', fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        for label in ax1.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
        
        # Average load comparison
        avg_loads = [data["statistics"]["avg_value"] for data in scenario_data.values()]
        bars = ax2.bar([name.replace("_", " ").title() for name in scenario_names], 
                      avg_loads, color=colors, alpha=0.7)
        
        for bar, avg in zip(bars, avg_loads):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{avg:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        ax2.set_title('Average System Load', fontweight='bold')
        ax2.set_ylabel('Average Load (%)', fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        for label in ax2.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
        
        # Max load comparison
        max_loads = [data["statistics"]["max_value"] for data in scenario_data.values()]
        bars = ax3.bar([name.replace("_", " ").title() for name in scenario_names], 
                      max_loads, color=colors, alpha=0.7)
        
        for bar, max_val in zip(bars, max_loads):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{max_val:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        ax3.set_title('Peak System Load', fontweight='bold')
        ax3.set_ylabel('Peak Load (%)', fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')
        
        for label in ax3.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
        
        # Spike count comparison
        spike_counts = [data["statistics"]["spike_count"] for data in scenario_data.values()]
        bars = ax4.bar([name.replace("_", " ").title() for name in scenario_names], 
                      spike_counts, color=colors, alpha=0.7)
        
        for bar, count in zip(bars, spike_counts):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{count}', ha='center', va='bottom', fontweight='bold')
        
        ax4.set_title('Total Spike Events', fontweight='bold')
        ax4.set_ylabel('Number of Spikes', fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
        
        for label in ax4.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.92, hspace=0.4, wspace=0.3)
        plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print(f"📊 Statistical summary graph saved to: {save_path}")
        
        return fig

def main():
    """Main function to generate spike pattern graphs"""
    
    print("🎯 SentinelLLM - Spike Pattern Graph Generator")
    print("=" * 50)
    
    # Generate data
    generator = SpikePatternGenerator()
    scenario_data = generator.generate_all_scenarios_data()
    
    # Create visualizations
    visualizer = GraphVisualizer()
    
    print("\n📈 Creating visualizations...")
    
    # Create output directory
    os.makedirs("graphs", exist_ok=True)
    
    # Generate all graphs
    visualizer.create_spike_timeline_graph(scenario_data, "graphs/spike_timeline.png")
    visualizer.create_comparative_analysis_graph(scenario_data, "graphs/comparative_analysis.png")
    visualizer.create_statistical_summary_graph(scenario_data, "graphs/statistical_summary.png")
    
    # Save data as JSON for further analysis
    json_data = {}
    for scenario, data in scenario_data.items():
        json_data[scenario] = {
            "values": data["values"],
            "statistics": data["statistics"],
            "config": data["config"]
        }
    
    with open("graphs/spike_data.json", "w") as f:
        json.dump(json_data, f, indent=2)
    
    print("\n✅ Graph generation completed!")
    print("📁 Files created:")
    print("   • graphs/spike_timeline.png - Individual scenario timelines")
    print("   • graphs/comparative_analysis.png - All scenarios compared")
    print("   • graphs/statistical_summary.png - Box plots and statistics")
    print("   • graphs/spike_data.json - Raw data for analysis")
    
    # Print statistics summary
    print("\n📊 Scenario Statistics:")
    print("-" * 60)
    for scenario, data in scenario_data.items():
        stats = data["statistics"]
        print(f"{scenario.replace('_', ' ').title():<20} | "
              f"Avg: {stats['avg_value']:5.1f}% | "
              f"Max: {stats['max_value']:5.1f}% | "
              f"Spikes: {stats['spike_count']:3d} "
              f"({stats['spike_percentage']:4.1f}%)")

if __name__ == "__main__":
    main()