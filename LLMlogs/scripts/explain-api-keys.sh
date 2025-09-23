#!/bin/bash

# SentinelLLM API Key Configuration Guide
# =====================================

echo "🔑 SentinelLLM API Key Configuration"
echo "===================================="

echo ""
echo "📋 Current API Key Status:"
echo "-------------------------"

# Check Grafana API Key
if grep -q "glsa_" /home/indresh/SentinelLLM/LLMlogs/.env; then
    echo "✅ Grafana API Key: CONFIGURED"
    echo "   Used for: Dashboard automation, alerts, programmatic access"
    echo "   Where: Internal system communication with Grafana"
else
    echo "❌ Grafana API Key: NOT CONFIGURED"
fi

echo ""
echo "🤖 AI Model Configuration:"
echo "-------------------------"
echo "✅ Qwen Model: LOCAL (No API key required)"
echo "   Model: qwen2-1.5b-log-classifier-Q5_K_M.gguf"
echo "   Location: Inside Docker container"
echo "   Classification: Runs completely offline"

echo ""
echo "❌ Gemini API Key: NOT NEEDED (Legacy configuration)"
echo "   Status: Removed from system"
echo "   Reason: Using local Qwen model instead"

echo ""
echo "🎯 How Anomaly Detection Works:"
echo "==============================="
echo "1. 📝 Log Producer → Generates sample logs → Kafka"
echo "2. 🤖 Log Consumer → Qwen model classifies → No API needed"
echo "3. 🔍 Anomaly Detector → ML models analyze patterns"
echo "4. 📊 Metrics → VictoriaMetrics → Grafana visualizes"
echo "5. 🚨 Alerts → Grafana uses API key for notifications"

echo ""
echo "📊 Where to See Anomaly Data:"
echo "============================"
echo "• Main Dashboard: http://localhost:3000/d/97421c11-7a01-414e-b607-3c701c9cc21f/"
echo "• Live Logs: http://localhost:3000/explore (select Loki data source)"
echo "• Metrics: http://localhost:8428/vmui (VictoriaMetrics UI)"

echo ""
echo "🔧 API Key Usage:"
echo "================"
echo "The Grafana API key is used by:"
echo "• Notifier service (for sending alerts)"
echo "• Dashboard automation"
echo "• Programmatic dashboard updates"
echo "• Creating annotations for patch deployments"

echo ""
echo "✅ No External API Keys Required!"
echo "All AI processing happens locally with Qwen model."