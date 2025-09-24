#!/bin/bash

# SentinelLLM Quick Start Script
# This script helps you get started with SentinelLLM quickly

set -e

echo "🚀 SentinelLLM Quick Start"
echo "=========================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker compose > /dev/null 2>&1; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your configuration before running services."
    
    # Using local Qwen model - no API key required
    echo "✅ Using local Qwen model for log classification"
else
    echo "📄 Found existing .env file"
fi

# Function to show available profiles
show_profiles() {
    echo ""
    echo "🎯 Available deployment profiles:"
    echo "1. basic     - Core services only (local log generation)"
    echo "2. aws       - Core + AWS CloudWatch integration"
    echo "3. azure     - Core + Azure Monitor integration" 
    echo "4. full      - All services (AWS + Azure + notifications)"
    echo ""
}

# Get deployment choice
if [ "$1" = "" ]; then
    show_profiles
    read -p "Choose deployment profile (1-4): " choice
else
    choice=$1
fi

# Set docker compose command based on choice
case $choice in
    1|basic)
        echo "🔄 Starting basic services..."
        COMPOSE_CMD="docker compose up -d --build"
        ;;
    2|aws)
        echo "🔄 Starting services with AWS integration..."
        COMPOSE_CMD="docker compose --profile aws up -d --build"
        ;;
    3|azure)
        echo "🔄 Starting services with Azure integration..."
        COMPOSE_CMD="docker compose --profile azure up -d --build"
        ;;
    4|full)
        echo "🔄 Starting all services..."
        COMPOSE_CMD="docker compose --profile aws --profile azure up -d --build"
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

# Execute the docker compose command
echo "⏳ Building and starting services..."
eval $COMPOSE_CMD

# Wait a moment for services to start
sleep 5

echo ""
echo "✅ SentinelLLM is starting up!"
echo ""
echo "📊 Access points:"
echo "- Grafana: http://localhost:3000 (admin/admin)"
echo "- VictoriaMetrics: http://localhost:8428"
echo ""
echo "🔍 Monitor logs:"
echo "docker compose logs -f log-consumer"
echo "docker compose logs -f notifier"
echo ""
echo "⏹️  Stop services:"
echo "docker compose down"
echo ""

# Check service status
echo "📋 Service status:"
docker compose ps

echo ""
echo "🎉 Setup complete! Check the logs to verify everything is working correctly."
