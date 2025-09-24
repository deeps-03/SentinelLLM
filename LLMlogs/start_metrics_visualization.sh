#!/bin/bash

# Demo Metrics Visualization Script
# Generates real-time graphs for all key metrics

echo "🎯 SentinelLLM - Real-time Metrics Visualization"
echo "================================================"

# Check if Python and required packages are available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is required but not installed"
    exit 1
fi

# Install required packages if not present
echo "📦 Installing required Python packages..."
pip3 install matplotlib numpy requests --quiet

# Check if VictoriaMetrics is running
echo "🔍 Checking VictoriaMetrics availability..."
if curl -s http://localhost:8428/api/v1/query > /dev/null 2>&1; then
    echo "✅ VictoriaMetrics is running - using real data"
    METRICS_SOURCE="real"
else
    echo "ℹ️  VictoriaMetrics not available - using synthetic data"
    METRICS_SOURCE="synthetic"
fi

echo ""
echo "🚀 Starting metrics visualization..."
echo "📊 Metrics to display:"
echo "   • CPU Usage (%)"
echo "   • Memory Usage (%)" 
echo "   • Disk Usage (%)"
echo "   • Network I/O (MB/s)"
echo "   • Error Rate (errors/min)"
echo "   • Response Time (ms)"
echo "   • Request Count (/min)"
echo "   • Log Classification Rate (%)"
echo "   • AI Confidence Score (%)"
echo ""
echo "💡 This will display real-time metrics in the terminal"
echo "🛑 Press Ctrl+C to stop monitoring"
echo ""

# Start the simple metrics monitor (no GUI dependencies)
python3 simple_metrics_monitor.py

echo ""
echo "✅ Visualization demo completed!"