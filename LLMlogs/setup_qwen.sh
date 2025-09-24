#!/bin/bash

# Qwen Model Setup Script
# Downloads and configures Qwen model for advanced log analysis

set -e

echo "🤖 Setting up Qwen model for advanced log analysis..."
echo "=================================================="

# Check if we're in the right directory
if [ ! -d "models" ]; then
    echo "❌ Error: models directory not found. Please run from LLMlogs directory."
    exit 1
fi

# Create models directory for Qwen if it doesn't exist
mkdir -p models/qwen

echo ""
echo "📦 Installing Qwen model dependencies..."
echo "----------------------------------------"
pip install -r requirements_qwen.txt

echo ""
echo "📥 Downloading Qwen 2.5 Code model (GGUF format)..."
echo "---------------------------------------------------"
# Download a reasonably sized Qwen model (1.5B parameters - good balance of size vs performance)
QWEN_MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
QWEN_MODEL_FILE="models/qwen/qwen-model.gguf"

if [ ! -f "$QWEN_MODEL_FILE" ]; then
    echo "Downloading Qwen 2.5 Coder model (1.5B parameters)..."
    curl -L -o "$QWEN_MODEL_FILE" "$QWEN_MODEL_URL"
    echo "✅ Qwen model downloaded successfully!"
else
    echo "✅ Qwen model already exists at $QWEN_MODEL_FILE"
fi

echo ""
echo "🔧 Updating Docker configuration for Qwen integration..."
echo "--------------------------------------------------------"

# Update the Dockerfile to include Qwen model
if [ -f "Dockerfile.simple_consumer" ]; then
    if ! grep -q "qwen-model.gguf" Dockerfile.simple_consumer; then
        echo "# Copy Qwen model" >> Dockerfile.simple_consumer
        echo "COPY models/qwen/qwen-model.gguf ./qwen-model.gguf" >> Dockerfile.simple_consumer
        echo "✅ Updated Dockerfile.simple_consumer with Qwen model"
    else
        echo "✅ Dockerfile already includes Qwen model"
    fi
fi

echo ""
echo "🧪 Testing Qwen model loading..."
echo "--------------------------------"
python3 -c "
try:
    from langchain_community.llms import LlamaCpp
    print('✅ LangChain dependencies available')
    
    # Test model loading
    import os
    if os.path.exists('$QWEN_MODEL_FILE'):
        print('✅ Qwen model file found')
        # Don't actually load the model here to save time
        print('🎯 Model setup complete - ready for integration!')
    else:
        print('❌ Qwen model file not found at $QWEN_MODEL_FILE')
except ImportError as e:
    print(f'❌ Missing dependencies: {e}')
    print('Please install requirements_qwen.txt')
"

echo ""
echo "🎉 Qwen Model Setup Complete!"
echo "============================="
echo ""
echo "📊 Model Details:"
echo "  - Model: Qwen 2.5 Coder (1.5B parameters)"
echo "  - Format: GGUF (optimized for CPU inference)"
echo "  - Size: ~1GB"
echo "  - Location: $QWEN_MODEL_FILE"
echo ""
echo "🚀 Next Steps:"
echo "  1. Rebuild Docker containers: docker compose build log-consumer"
echo "  2. Restart services: docker compose up -d"
echo "  3. Watch logs for 'Qwen LLM model initialized successfully!'"
echo ""
echo "💡 The system will now provide AI-powered detailed solutions for:"
echo "   - ⚠️  WARNING logs → Preventive action recommendations"  
echo "   - 🚨 INCIDENT logs → Emergency response procedures"
echo ""