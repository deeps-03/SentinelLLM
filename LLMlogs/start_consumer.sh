#!/bin/bash

# Start SentinelLLM Consumer Service
echo "🚀 Starting SentinelLLM Consumer Service..."

cd /home/indresh/project/SentinelLLM/LLMlogs

# Activate virtual environment
source venv/bin/activate

# Start the consumer
echo "Starting AI-powered log consumer..."
python simple_consumer.py
