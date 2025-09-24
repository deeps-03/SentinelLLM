#!/bin/bash

# ==============================================================================
# SentinelLLM - Presentation Demo Script
# ==============================================================================
# This script demonstrates the complete SentinelLLM system for presentations
# Fixed all issues: No Gemini API key needed, working log consumer, clean structure
# ==============================================================================

set -e

echo "🎯 SentinelLLM - PRESENTATION DEMO"
echo "=================================="
echo "🚀 AI-Powered Log Anomaly Detection System"
echo "✅ All issues fixed - Ready for presentation!"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        print_error "Docker Compose is not installed" 
        exit 1
    fi
    
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Clean up any existing containers
cleanup_existing() {
    print_info "Cleaning up existing containers..."
    docker compose down --remove-orphans > /dev/null 2>&1 || true
    print_status "Cleanup completed"
}

# Start the system
start_system() {
    print_info "Starting SentinelLLM system..."
    print_info "This may take a few minutes on first run (downloading models)..."
    
    docker compose up -d --build
    
    if [ $? -eq 0 ]; then
        print_status "SentinelLLM system started successfully"
    else
        print_error "Failed to start system"
        exit 1
    fi
}

# Wait for services to be ready
wait_for_services() {
    print_info "Waiting for services to be ready..."
    
    # Wait for Grafana
    print_info "Waiting for Grafana..."
    for i in {1..30}; do
        if curl -s http://localhost:3000/api/health > /dev/null; then
            print_status "Grafana is ready"
            break
        fi
        sleep 2
        echo -n "."
    done
    
    # Wait for VictoriaMetrics
    print_info "Waiting for VictoriaMetrics..."
    for i in {1..30}; do
        if curl -s http://localhost:8428/health > /dev/null; then
            print_status "VictoriaMetrics is ready"
            break
        fi
        sleep 2
        echo -n "."
    done
}

# Setup Grafana API key and data sources
setup_grafana() {
    print_info "Setting up Grafana..."
    
    # Create service account
    SA_RESPONSE=$(curl -s -X POST http://localhost:3000/api/serviceaccounts \
        -H "Content-Type: application/json" \
        -u admin:admin \
        -d '{"name": "SentinelLLM-Demo", "role": "Admin"}' 2>/dev/null)
    
    if echo "$SA_RESPONSE" | grep -q '"id"'; then
        SA_ID=$(echo "$SA_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)
        
        # Create token
        TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:3000/api/serviceaccounts/$SA_ID/tokens" \
            -H "Content-Type: application/json" \
            -u admin:admin \
            -d '{"name": "demo-token"}' 2>/dev/null)
        
        if echo "$TOKEN_RESPONSE" | grep -q '"key"'; then
            API_KEY=$(echo "$TOKEN_RESPONSE" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)
            echo "GRAFANA_API_KEY=$API_KEY" >> .env
            print_status "Grafana API key created and saved"
            
            # Add VictoriaMetrics data source
            curl -s -X POST http://localhost:3000/api/datasources \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $API_KEY" \
                -d '{
                  "name": "VictoriaMetrics",
                  "type": "prometheus", 
                  "url": "http://victoria-metrics:8428",
                  "access": "proxy",
                  "isDefault": true
                }' > /dev/null
            
            print_status "Data source configured"
        fi
    fi
}

# Start metrics generation
start_metrics_generator() {
    print_info "Starting metrics generator..."
    python3 scripts/metrics_generator.py &
    METRICS_PID=$!
    echo $METRICS_PID > /tmp/metrics_pid
    print_status "Metrics generator started (PID: $METRICS_PID)"
}

# Show system status
show_status() {
    echo ""
    echo "🎯 DEMO SYSTEM STATUS"
    echo "===================="
    
    # Check service status
    docker compose ps
    
    echo ""
    echo "📊 ACCESS POINTS:"
    echo "================="
    echo "🌐 Grafana Dashboard: http://localhost:3000"
    echo "   Username: admin | Password: admin"
    echo ""
    echo "📈 VictoriaMetrics:   http://localhost:8428"
    echo "📝 Kafka UI:          http://localhost:9092 (internal)"
    echo ""
    
    echo "🎥 DEMO FLOW:"
    echo "============="
    echo "1. 📝 Log Producer → Generates realistic application logs"
    echo "2. 🤖 Log Consumer → XGBoost classifies logs (LOCAL AI - no API keys!)"
    echo "3. 🔍 Anomaly Detector → Detects patterns and spikes"
    echo "4. 📊 VictoriaMetrics → Stores metrics"
    echo "5. 🎨 Grafana → Visualizes real-time anomaly detection"
    echo ""
    
    # Check for metrics
    sleep 5
    METRICS_COUNT=$(curl -s "http://localhost:8428/api/v1/label/__name__/values" | grep -o '"[^"]*"' | wc -l)
    if [ "$METRICS_COUNT" -gt 5 ]; then
        print_status "Metrics are flowing ($METRICS_COUNT metric types detected)"
    else
        print_warning "Metrics not yet available (may take a moment)"
    fi
}

# Demo interaction commands
show_demo_commands() {
    echo ""
    echo "🎮 DEMO COMMANDS:"
    echo "================"
    echo "View logs:     docker compose logs -f log-consumer"
    echo "View metrics:  docker compose logs -f anomaly-detector" 
    echo "Restart:       docker compose restart"
    echo "Stop demo:     docker compose down"
    echo "Clean all:     docker compose down --volumes --remove-orphans"
    echo ""
    echo "📊 PRESENTATION POINTS:"
    echo "======================"
    echo "• ✅ LOCAL AI: No external APIs - Qwen + XGBoost models"
    echo "• 🚀 REAL-TIME: Live log classification and anomaly detection"
    echo "• 📈 SCALABLE: Kafka-based architecture"
    echo "• 🎯 ML-POWERED: Multiple anomaly detection algorithms"
    echo "• 📊 VISUAL: Beautiful Grafana dashboards"
    echo "• 🔧 PRODUCTION-READY: Docker containerized"
}

# Cleanup function for graceful shutdown
cleanup() {
    print_info "Cleaning up demo..."
    if [ -f /tmp/metrics_pid ]; then
        METRICS_PID=$(cat /tmp/metrics_pid)
        kill $METRICS_PID 2>/dev/null || true
        rm /tmp/metrics_pid
    fi
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Main demo execution
main() {
    echo ""
    check_prerequisites
    cleanup_existing
    start_system
    wait_for_services
    setup_grafana
    start_metrics_generator
    show_status
    show_demo_commands
    
    echo ""
    print_status "🎉 DEMO READY FOR PRESENTATION!"
    echo ""
    print_info "Press Ctrl+C to stop the demo"
    
    # Keep running until interrupted
    while true; do
        sleep 30
        # Optionally show live stats
        INCIDENT_COUNT=$(curl -s "http://localhost:8428/api/v1/query?query=log_incident_total" 2>/dev/null | grep -o '"value":\[[^]]*\]' | tail -1 | grep -o '[0-9.]*' | tail -1 2>/dev/null || echo "0")
        if [ ! -z "$INCIDENT_COUNT" ] && [ "$INCIDENT_COUNT" != "0" ]; then
            print_info "Live Stats: $INCIDENT_COUNT incidents detected"
        fi
    done
}

# Show usage if --help
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "SentinelLLM Presentation Demo"
    echo "Usage: $0 [--help]"
    echo ""
    echo "This script starts the complete SentinelLLM system for demonstration."
    echo "All components will be available for live presentation."
    exit 0
fi

main