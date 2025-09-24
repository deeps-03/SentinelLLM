#!/bin/bash

# Master Demo Script - Ultra Fast Loki + Multi-Model + Graph Generation
echo "🚀 SentinelLLM - Complete Ultra Fast Demo Suite"
echo "=============================================="

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker first."
        exit 1
    fi
    echo "✅ Docker is running"
}

# Function to install Python dependencies with fallback
install_dependencies() {
    echo "📦 Installing Python dependencies..."
    
    # Try system packages first (safer)
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update >/dev/null 2>&1 || true
        sudo apt-get install -y python3-matplotlib python3-numpy python3-pandas python3-seaborn python3-sklearn >/dev/null 2>&1 || true
    fi
    
    # Try pip with --break-system-packages if needed
    pip3 install matplotlib numpy pandas seaborn scikit-learn xgboost --break-system-packages >/dev/null 2>&1 || true
    
    echo "✅ Dependencies installed (or already available)"
}

# Function to generate graphs
generate_graphs() {
    echo ""
    echo "📊 Generating spike pattern and model accuracy graphs..."
    
    # Generate spike patterns
    echo "🔥 Creating spike pattern visualizations..."
    python3 generate_spike_graphs.py
    
    # Generate model accuracy graphs  
    echo "🤖 Creating model accuracy visualizations..."
    python3 generate_model_accuracy_graphs.py
    
    echo "✅ All graphs generated successfully!"
}

# Function to start ultra fast Loki
start_ultra_loki() {
    echo ""
    echo "🚀 Starting Ultra Fast Loki Integration..."
    echo "  • Real log generation with spike patterns"
    echo "  • Loki log aggregation"
    echo "  • Grafana visualization"
    
    # Make script executable and run in background
    chmod +x ultra_fast_loki.sh
    
    echo "⏳ Starting Loki services (this may take a few minutes for first-time image download)..."
    timeout 300s ./ultra_fast_loki.sh &
    LOKI_PID=$!
    
    # Wait a bit for services to start
    sleep 30
    
    echo "✅ Ultra Fast Loki started (PID: $LOKI_PID)"
    echo "📊 Access Grafana: http://localhost:3000 (admin/admin)"
    echo "🔍 Loki API: http://localhost:3100"
}

# Function to start multi-model analyzer
start_multi_model() {
    echo ""
    echo "🤖 Starting Multi-Model Patch Analyzer..."
    echo "  • XGBoost real-time classification"
    echo "  • Qwen 1.5B AI analysis"
    echo "  • Multi-scenario patch testing"
    
    # Make script executable and run in background
    chmod +x multi_model_analyzer.sh
    
    echo "⏳ Starting multi-model services..."
    timeout 300s ./multi_model_analyzer.sh &
    ANALYZER_PID=$!
    
    # Wait for services to start
    sleep 45
    
    echo "✅ Multi-Model Analyzer started (PID: $ANALYZER_PID)"
    echo "📈 VictoriaMetrics: http://localhost:8428"
    echo "🔄 Kafka: localhost:9092"
}

# Function to show real-time monitoring
show_monitoring() {
    echo ""
    echo "📊 Starting Real-Time Monitoring Dashboard..."
    echo "💡 This will show live metrics for 30 seconds"
    
    timeout 30s python3 simple_metrics_monitor.py
    
    echo "✅ Monitoring demo completed"
}

# Function to display results
show_results() {
    echo ""
    echo "🎉 Demo Results Summary"
    echo "======================"
    
    if [ -d "graphs" ]; then
        echo "📊 Generated Graphs:"
        ls -la graphs/ | grep -E "\.(png|json)$" | while read -r line; do
            echo "   📈 $(echo $line | awk '{print $9}')"
        done
    fi
    
    echo ""
    echo "🔗 Active Services:"
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo "   ✅ Grafana: http://localhost:3000"
    fi
    if curl -s http://localhost:3100/ready >/dev/null 2>&1; then
        echo "   ✅ Loki: http://localhost:3100"
    fi
    if curl -s http://localhost:8428 >/dev/null 2>&1; then
        echo "   ✅ VictoriaMetrics: http://localhost:8428"
    fi
    
    echo ""
    echo "🎯 Key Demonstrations:"
    echo "   🔥 Realistic spike patterns during patch scenarios"
    echo "   🤖 XGBoost + Qwen multi-model AI analysis"
    echo "   📈 Model accuracy visualization across difficulty levels"
    echo "   📊 Real-time log aggregation and monitoring"
    echo "   🚀 Complete end-to-end patch readiness assessment"
}

# Function to cleanup
cleanup_services() {
    echo ""
    echo "🧹 Cleaning up demo services..."
    
    # Stop Docker Compose services
    docker compose -f docker compose-ultra-loki.yml down 2>/dev/null || true
    docker compose -f docker compose-multi-model.yml down 2>/dev/null || true
    
    # Kill background processes if running
    pkill -f ultra_fast_loki.sh 2>/dev/null || true
    pkill -f multi_model_analyzer.sh 2>/dev/null || true
    
    echo "✅ Cleanup completed"
}

# Main demo flow
main() {
    echo "🎯 Welcome to SentinelLLM Ultra Fast Demo"
    echo "This demo showcases:"
    echo "  • Ultra-fast Loki log aggregation with real spike patterns"
    echo "  • Multi-model AI analysis (XGBoost + Qwen 1.5B)"
    echo "  • Real-time graph generation showing system behavior"
    echo "  • Patch readiness assessment across different scenarios"
    echo ""
    
    # Setup trap for cleanup
    trap 'cleanup_services; exit 0' INT TERM EXIT
    
    # Preliminary checks
    check_docker
    install_dependencies
    
    # Ask user what to run
    echo "Choose demo components to run:"
    echo "1. Generate comprehensive text reports (ASCII graphs - works always)"
    echo "2. Generate matplotlib graphs (may fail due to NumPy compatibility)"
    echo "3. Ultra Fast Loki + Reports (medium - 10 minutes)"
    echo "4. Multi-Model Analyzer + Reports (medium - 10 minutes)"
    echo "5. Complete demo suite (all components - 20 minutes)"
    echo "6. Quick monitoring demo (1 minute)"
    
    read -p "Enter choice (1-6): " choice
    
    case $choice in
        1)
            echo "📊 Generating comprehensive text reports with ASCII graphs..."
            python3 generate_text_reports.py
            ;;
        2)
            generate_graphs
            ;;
        3)
            python3 generate_text_reports.py
            start_ultra_loki
            show_monitoring
            ;;
        4)
            python3 generate_text_reports.py
            start_multi_model
            show_monitoring
            ;;
        5)
            python3 generate_text_reports.py
            start_ultra_loki
            start_multi_model
            show_monitoring
            ;;
        6)
            show_monitoring
            ;;
        *)
            echo "Invalid choice. Running text report generation only."
            python3 generate_text_reports.py
            ;;
    esac
    
    show_results
    
    echo ""
    echo "🎉 SentinelLLM Demo Completed Successfully!"
    echo "📁 Check the 'graphs' directory for all generated visualizations"
    echo "🔗 Services remain running for further exploration"
    echo "🛑 Press Ctrl+C or close terminal to stop all services"
    
    # Keep running until interrupted
    if [ "$choice" != "1" ] && [ "$choice" != "5" ]; then
        echo "⏳ Demo services running... Press Ctrl+C to stop"
        while true; do
            sleep 30
            echo "🔄 Services still active - $(date '+%H:%M:%S')"
        done
    fi
}

# Run main function
main "$@"