#!/bin/bash

echo "🧹 Cleaning SentinelLLM Project Structure for Presentation"
echo "=========================================================="

# Create organized directory structure
mkdir -p {core,tests,scripts,configs,models,docs}

echo "📁 Organizing files..."

# Core application files
echo "Moving core application files..."
mv log_producer.py core/ 2>/dev/null || true
mv simple_consumer.py core/ 2>/dev/null || true
mv anomaly_detector.py core/ 2>/dev/null || true
mv notifier.py core/ 2>/dev/null || true
mv patch_analyzer.py core/ 2>/dev/null || true
mv multi_model_anomaly_detector.py core/ 2>/dev/null || true

# Test files
echo "Moving test files..."
mv test_*.py tests/ 2>/dev/null || true
mv *test*.py tests/ 2>/dev/null || true

# Utility scripts
echo "Moving utility scripts..."
mv metrics_generator.py scripts/ 2>/dev/null || true
mv model_train.py scripts/ 2>/dev/null || true
mv *demo*.sh scripts/ 2>/dev/null || true
mv *api*.sh scripts/ 2>/dev/null || true
mv explain*.sh scripts/ 2>/dev/null || true

# Configuration files
echo "Moving configuration files..."
mv *.yml configs/ 2>/dev/null || true
mv *.yaml configs/ 2>/dev/null || true
mv docker-compose.yml . # Keep main compose file in root
mv configs/docker-compose.yml . 2>/dev/null || true

# ML Models
echo "Moving ML models..."
mv *.pkl models/ 2>/dev/null || true
mv *.gguf models/ 2>/dev/null || true

# Documentation
echo "Moving documentation..."
mv *.md docs/ 2>/dev/null || true
mv README.md . # Keep main README in root
mv docs/README.md . 2>/dev/null || true

# Cloud provider specific (optional - can be moved to separate folder)
mkdir -p integrations
mv aws_log_poller.py integrations/ 2>/dev/null || true
mv azure_log_poller.py integrations/ 2>/dev/null || true
mv loki_kafka_forwarder.py integrations/ 2>/dev/null || true
mv ultra_fast_loki.py integrations/ 2>/dev/null || true

# Remove unnecessary files
echo "🗑️  Removing unnecessary files..."
rm -f *.log 2>/dev/null || true
rm -f *.tmp 2>/dev/null || true
rm -f *~ 2>/dev/null || true

# Files to keep in root
ROOT_FILES="
docker-compose.yml
.env
.env.example
requirements.txt
requirements_simple.txt
Dockerfile.*
quick-start.sh
quick-start.ps1
README.md
"

echo ""
echo "✅ Project structure organized!"
echo ""
echo "📂 New Structure:"
echo "├── core/              # Main application files"
echo "├── tests/             # Test files"  
echo "├── scripts/           # Utility scripts"
echo "├── configs/           # Configuration files"
echo "├── models/            # ML models and weights"
echo "├── integrations/      # Cloud provider integrations"
echo "├── docs/              # Documentation"
echo "└── [root files]       # Docker, configs, startup scripts"

echo ""
echo "🎯 Ready for presentation!"