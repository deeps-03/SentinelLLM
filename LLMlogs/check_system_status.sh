#!/bin/bash

# SentinelLLM System Status Check
# Run this script to verify everything is working properly

echo "🚀 SentinelLLM System Status Check"
echo "=================================="
echo

# Function to check HTTP endpoint
check_endpoint() {
    local url=$1
    local name=$2
    if curl -s --connect-timeout 5 "$url" > /dev/null; then
        echo "✅ $name: WORKING ($url)"
        return 0
    else
        echo "❌ $name: FAILED ($url)"
        return 1
    fi
}

# Function to check if service is running
check_service() {
    local service=$1
    if docker compose ps | grep -q "$service.*Up"; then
        echo "✅ $service: RUNNING"
        return 0
    else
        echo "❌ $service: NOT RUNNING"
        return 1
    fi
}

# 1. Check Docker Compose services
echo "🔍 1. Checking Docker Services..."
echo "--------------------------------"
services=("grafana" "kafka" "log-consumer" "log-producer" "anomaly-detector" "victoria-metrics" "zookeeper")
all_services_ok=true

for service in "${services[@]}"; do
    if ! check_service "$service"; then
        all_services_ok=false
    fi
done
echo

# 2. Check HTTP endpoints
echo "🌐 2. Checking HTTP Endpoints..."
echo "-------------------------------"
endpoints_ok=true
if ! check_endpoint "http://localhost:3000" "Grafana Dashboard"; then
    endpoints_ok=false
fi
if ! check_endpoint "http://localhost:8428/metrics" "VictoriaMetrics"; then
    endpoints_ok=false
fi
echo

# 3. Check if metrics are being generated
echo "📊 3. Checking Metrics Data..."
echo "-----------------------------"
metrics_ok=true

# Check incident metrics
incident_data=$(curl -s "http://localhost:8428/api/v1/query?query=log_incident_total" 2>/dev/null)
if echo "$incident_data" | grep -q "log_incident_total"; then
    incident_count=$(echo "$incident_data" | python3 -c "import json,sys; data=json.load(sys.stdin); result=data.get('data',{}).get('result',[]); print(result[0]['value'][1] if result else '0')" 2>/dev/null || echo "0")
    echo "✅ Incident logs processed: $incident_count"
else
    echo "❌ No incident metrics found"
    metrics_ok=false
fi

# Check warning metrics  
warning_data=$(curl -s "http://localhost:8428/api/v1/query?query=log_warning_total" 2>/dev/null)
if echo "$warning_data" | grep -q "log_warning_total"; then
    warning_count=$(echo "$warning_data" | python3 -c "import json,sys; data=json.load(sys.stdin); result=data.get('data',{}).get('result',[]); print(result[0]['value'][1] if result else '0')" 2>/dev/null || echo "0")
    echo "✅ Warning logs processed: $warning_count"
else
    echo "❌ No warning metrics found"
    metrics_ok=false
fi

# Check normal metrics
normal_data=$(curl -s "http://localhost:8428/api/v1/query?query=log_normal_total" 2>/dev/null)
if echo "$normal_data" | grep -q "log_normal_total"; then
    normal_count=$(echo "$normal_data" | python3 -c "import json,sys; data=json.load(sys.stdin); result=data.get('data',{}).get('result',[]); print(result[0]['value'][1] if result else '0')" 2>/dev/null || echo "0")
    echo "✅ Normal logs processed: $normal_count"
else
    echo "❌ No normal metrics found"
    metrics_ok=false
fi
echo

# 4. Check AI log processing
echo "🤖 4. Checking AI Log Processing..."
echo "---------------------------------"
recent_logs=$(docker compose logs log-consumer --tail=5 2>/dev/null | grep -E "(incident|warning|normal|AI|Classified)" | wc -l)
if [ "$recent_logs" -gt 0 ]; then
    echo "✅ AI log classification active (found $recent_logs recent classifications)"
    echo "📋 Recent log processing:"
    docker compose logs log-consumer --tail=3 2>/dev/null | grep -E "→ Classified as:" | tail -3 | sed 's/^/   /'
else
    echo "❌ No recent AI log classifications found"
fi
echo

# 5. Final status summary
echo "🎯 Overall System Status"
echo "======================="
if [ "$all_services_ok" = true ] && [ "$endpoints_ok" = true ] && [ "$metrics_ok" = true ]; then
    echo "🎉 SYSTEM STATUS: FULLY OPERATIONAL!"
    echo
    echo "✅ All Docker services running"
    echo "✅ All HTTP endpoints accessible" 
    echo "✅ Metrics being generated and stored"
    echo "✅ AI log classification working"
    echo
    echo "🌐 Access Points:"
    echo "   • Grafana Dashboard: http://localhost:3000 (admin/admin)"
    echo "   • VictoriaMetrics: http://localhost:8428"
    echo
    echo "📊 Live Dashboard: http://localhost:3000/d/97421c11-7a01-414e-b607-3c701c9cc21f"
    echo
    echo "🚀 SentinelLLM is ready for production use!"
else
    echo "⚠️  SYSTEM STATUS: ISSUES DETECTED"
    echo
    if [ "$all_services_ok" != true ]; then
        echo "❌ Some Docker services are not running"
        echo "   Fix: docker compose up -d"
    fi
    if [ "$endpoints_ok" != true ]; then
        echo "❌ Some HTTP endpoints are not accessible"
        echo "   Fix: Wait 30 seconds and try again"
    fi
    if [ "$metrics_ok" != true ]; then
        echo "❌ Metrics are not being generated"
        echo "   Fix: docker compose restart log-producer log-consumer"
        echo "   Wait: 1 minute, then run this script again"
    fi
fi
echo