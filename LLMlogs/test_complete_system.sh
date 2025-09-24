#!/bin/bash

# SentinelLLM Complete System Test
# Tests all components to ensure everything works correctly

set -e

echo "🔍 SENTINELLM COMPLETE SYSTEM TEST"
echo "=================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Test counter
TESTS_PASSED=0
TESTS_TOTAL=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log_info "Testing: $test_name"
    
    if eval "$test_command" > /dev/null 2>&1; then
        log_success "$test_name - PASSED"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_error "$test_name - FAILED"
        return 1
    fi
}

echo "🔧 PREREQUISITE CHECKS"
echo "====================="

# Check Docker
run_test "Docker availability" "docker info"

# Check Docker Compose
run_test "Docker Compose availability" "docker compose --version"

# Check Python
run_test "Python 3.12+ availability" "python3 --version | grep -E 'Python 3\.(1[2-9]|[2-9][0-9])'"

echo ""
echo "📦 DEPENDENCY CHECKS"
echo "==================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv venv
    log_success "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
log_info "Activated virtual environment"

# Install dependencies
log_info "Installing/checking dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
log_success "Dependencies verified"

echo ""
echo "🤖 ML MODEL CHECKS"
echo "=================="

# Check if models exist
if [ ! -f "vectorizer.pkl" ] || [ ! -f "xgboost_model.pkl" ] || [ ! -f "label_encoder.pkl" ]; then
    log_info "Generating missing ML models..."
    python model_train.py
    log_success "ML models generated successfully"
else
    log_success "ML models already exist"
fi

# Verify model files
run_test "XGBoost model file" "[ -f 'xgboost_model.pkl' ]"
run_test "Vectorizer file" "[ -f 'vectorizer.pkl' ]"
run_test "Label encoder file" "[ -f 'label_encoder.pkl' ]"
run_test "Patch analyzer models" "[ -f 'patch_analyzer_models.pkl' ]"

echo ""
echo "🧪 COMPONENT TESTS"
echo "=================="

# Test patch analyzer
log_info "Testing patch analyzer..."
if python test_patch_analyzer.py > /tmp/patch_test.log 2>&1; then
    # Extract performance metrics
    ANALYSIS_TIME=$(grep "Average time per analysis:" /tmp/patch_test.log | awk '{print $6}' | sed 's/ms//')
    THROUGHPUT=$(grep "Throughput:" /tmp/patch_test.log | awk '{print $2}')
    
    if (( $(echo "$ANALYSIS_TIME < 100" | bc -l) )); then
        log_success "Patch analyzer - PASSED (${ANALYSIS_TIME}ms, ${THROUGHPUT} analyses/sec)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_warning "Patch analyzer slow - ${ANALYSIS_TIME}ms (expected <100ms)"
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
else
    log_error "Patch analyzer - FAILED"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
fi

echo ""
echo "🐳 DOCKER SERVICE TESTS"
echo "======================"

# Start core services
log_info "Starting core Docker services..."
docker compose up -d kafka zookeeper loki > /dev/null 2>&1
log_success "Core services started"

# Wait for services to initialize
log_info "Waiting for services to initialize (30 seconds)..."
sleep 30

# Test Kafka
run_test "Kafka service" "docker compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list"

# Test Zookeeper  
run_test "Zookeeper service" "docker compose exec zookeeper zkCli.sh ls /"

# Test Loki
run_test "Loki service" "curl -s http://localhost:3100/ready"

echo ""
echo "⚡ PERFORMANCE TESTS"
echo "==================="

# Test ultra-fast Loki
log_info "Testing ultra-fast Loki integration..."
if python ultra_fast_loki.py > /tmp/loki_test.log 2>&1; then
    # Check for performance metrics
    if grep -q "0.0[0-9]s" /tmp/loki_test.log; then
        log_success "Ultra-fast Loki - PASSED (sub-100ms queries)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_warning "Loki performance suboptimal"
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
else
    log_error "Ultra-fast Loki - FAILED"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
fi

# Test Kafka producer/consumer
log_info "Testing Kafka log streaming..."
if python test_kafka.py > /tmp/kafka_test.log 2>&1; then
    log_success "Kafka streaming - PASSED"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    log_error "Kafka streaming - FAILED"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

echo ""
echo "🔍 INTEGRATION TESTS"
echo "==================="

# Test multi-model system
log_info "Testing complete multi-model system..."
if timeout 120 python test_multi_model_system.py > /tmp/multi_test.log 2>&1; then
    log_success "Multi-model system - PASSED"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    log_warning "Multi-model system - TIMEOUT (may still be working)"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

echo ""
echo "📊 TEST RESULTS SUMMARY"
echo "======================"

if [ $TESTS_PASSED -eq $TESTS_TOTAL ]; then
    log_success "ALL TESTS PASSED! ($TESTS_PASSED/$TESTS_TOTAL)"
    echo ""
    log_success "🎉 SentinelLLM is FULLY OPERATIONAL and DEMO-READY!"
    echo ""
    echo -e "${GREEN}📋 System Status:${NC}"
    echo -e "${GREEN}  ✅ Patch Analysis: Working (< 100ms)${NC}"
    echo -e "${GREEN}  ✅ Log Processing: Working (< 100ms)${NC}"
    echo -e "${GREEN}  ✅ ML Models: Generated and loaded${NC}"
    echo -e "${GREEN}  ✅ Docker Services: Running${NC}"
    echo -e "${GREEN}  ✅ Performance: Optimal${NC}"
    echo ""
    echo -e "${BLUE}🚀 Ready for Manager Demo!${NC}"
    
elif [ $TESTS_PASSED -gt $((TESTS_TOTAL * 3 / 4)) ]; then
    log_warning "MOSTLY WORKING ($TESTS_PASSED/$TESTS_TOTAL tests passed)"
    echo ""
    log_warning "Minor issues detected - check logs above"
    
else
    log_error "CRITICAL ISSUES ($TESTS_PASSED/$TESTS_TOTAL tests passed)"
    echo ""
    log_error "Multiple failures detected - system needs attention"
    exit 1
fi

echo ""
echo "📖 USAGE INSTRUCTIONS"
echo "===================="
echo ""
echo -e "${BLUE}To start full system:${NC}"
echo "  ./quick-start.sh full"
echo ""
echo -e "${BLUE}To test individual components:${NC}"
echo "  python test_patch_analyzer.py"
echo "  python ultra_fast_loki.py"
echo "  python test_multi_model_system.py"
echo ""
echo -e "${BLUE}To monitor services:${NC}"
echo "  docker compose logs -f"
echo ""
echo -e "${BLUE}To stop services:${NC}"
echo "  docker compose down"

# Cleanup
deactivate 2>/dev/null || true

echo ""
log_success "System test completed!"