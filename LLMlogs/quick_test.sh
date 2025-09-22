#!/bin/bash

# SentinelLLM Quick Test - Core Functionality Only
# Tests essential components without heavy dependencies

set -e

echo "⚡ SENTINELLM QUICK FUNCTIONALITY TEST"
echo "====================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

TESTS_PASSED=0
TESTS_TOTAL=0

# Quick test function
quick_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log_info "Testing: $test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        log_success "$test_name - PASSED"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_error "$test_name - FAILED"
    fi
}

echo "🔧 BASIC CHECKS"
echo "=============="

# Check Docker
quick_test "Docker availability" "docker info"
quick_test "Docker Compose availability" "docker-compose --version"

echo ""
echo "📂 FILE STRUCTURE"
echo "================"

# Check essential files
quick_test "Patch analyzer exists" "[ -f 'patch_analyzer.py' ]"
quick_test "Ultra-fast Loki exists" "[ -f 'ultra_fast_loki.py' ]"
quick_test "Model training script exists" "[ -f 'model_train.py' ]"
quick_test "Docker compose config" "[ -f 'docker-compose.yml' ]"
quick_test "Requirements file" "[ -f 'requirements.txt' ]"

# Check model files
quick_test "XGBoost model" "[ -f 'xgboost_model.pkl' ]"
quick_test "Vectorizer model" "[ -f 'vectorizer.pkl' ]" 
quick_test "Label encoder" "[ -f 'label_encoder.pkl' ]"
quick_test "Patch analyzer models" "[ -f 'patch_analyzer_models.pkl' ]"

echo ""
echo "🐳 DOCKER SERVICES"
echo "=================="

# Start core services
log_info "Starting core Docker services (Kafka, Zookeeper, Loki)..."
if docker-compose up -d kafka zookeeper loki >/dev/null 2>&1; then
    log_success "Docker services started"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    log_error "Docker services failed to start"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Wait for services
log_info "Waiting for services to initialize (20 seconds)..."
sleep 20

# Test service availability
quick_test "Kafka running" "docker-compose ps kafka | grep -q Up"
quick_test "Zookeeper running" "docker-compose ps zookeeper | grep -q Up"  
quick_test "Loki running" "docker-compose ps loki | grep -q Up"

echo ""
echo "🔌 SERVICE CONNECTIVITY"
echo "======================"

# Test Loki connectivity
if curl -s http://localhost:3100/ready | grep -q ready; then
    log_success "Loki connectivity - PASSED"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    log_error "Loki connectivity - FAILED"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

echo ""
echo "🧪 CORE FUNCTIONALITY"  
echo "===================="

# Test if Python scripts can import basic modules (without running full tests)
if python3 -c "import sys; sys.path.append('.'); import patch_analyzer; print('Import successful')" >/dev/null 2>&1; then
    log_success "Patch analyzer imports - PASSED"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    log_error "Patch analyzer imports - FAILED (may need venv activation)"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

echo ""
echo "📋 TEST SUMMARY"
echo "==============="

PASS_RATE=$(( (TESTS_PASSED * 100) / TESTS_TOTAL ))

if [ $TESTS_PASSED -eq $TESTS_TOTAL ]; then
    log_success "ALL TESTS PASSED! ($TESTS_PASSED/$TESTS_TOTAL - 100%)"
    echo ""
    log_success "🎉 SentinelLLM CORE FUNCTIONALITY IS WORKING!"
    
elif [ $PASS_RATE -gt 75 ]; then
    echo -e "${YELLOW}⚠️  MOSTLY WORKING ($TESTS_PASSED/$TESTS_TOTAL - ${PASS_RATE}%)${NC}"
    echo ""
    echo -e "${YELLOW}Minor issues detected but core functionality appears operational${NC}"
    
else
    log_error "MULTIPLE ISSUES ($TESTS_PASSED/$TESTS_TOTAL - ${PASS_RATE}%)"
    echo ""
    log_error "Core issues detected - system needs attention"
    exit 1
fi

echo ""
echo "📖 NEXT STEPS"
echo "============="
echo ""
echo -e "${BLUE}To run full system with dependencies:${NC}"
echo "  1. source venv/bin/activate"
echo "  2. pip install -r requirements.txt"
echo "  3. python model_train.py  # Generate ML models"
echo "  4. python test_patch_analyzer.py"
echo "  5. python ultra_fast_loki.py"
echo ""
echo -e "${BLUE}To start complete system:${NC}"
echo "  ./quick-start.sh full"
echo ""
echo -e "${BLUE}To stop services:${NC}"
echo "  docker-compose down"

echo ""
log_success "Quick test completed!"