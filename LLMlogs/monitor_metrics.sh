#!/bin/bash

# Real-time SentinelLLM Metrics Monitor
echo "🚀 SentinelLLM Live Metrics Dashboard"
echo "======================================"

while true; do
    clear
    echo "🚀 SentinelLLM Live Metrics - $(date)"
    echo "======================================"
    
    # Get current metrics
    INCIDENTS=$(curl -s "http://localhost:8428/api/v1/query?query=log_incident_total" | grep -o '"value":\[[^,]*,"[^"]*"' | grep -o '"[^"]*"$' | tr -d '"')
    WARNINGS=$(curl -s "http://localhost:8428/api/v1/query?query=log_warning_total" | grep -o '"value":\[[^,]*,"[^"]*"' | grep -o '"[^"]*"$' | tr -d '"')  
    NORMAL=$(curl -s "http://localhost:8428/api/v1/query?query=log_normal_total" | grep -o '"value":\[[^,]*,"[^"]*"' | grep -o '"[^"]*"$' | tr -d '"')
    
    echo "🚨 INCIDENTS: ${INCIDENTS:-0}"
    echo "⚠️  WARNINGS:  ${WARNINGS:-0}"
    echo "ℹ️  NORMAL:    ${NORMAL:-0}"
    echo ""
    
    TOTAL=$((${INCIDENTS:-0} + ${WARNINGS:-0} + ${NORMAL:-0}))
    echo "📊 TOTAL PROCESSED: $TOTAL"
    
    if [ $TOTAL -gt 0 ]; then
        INCIDENT_PCT=$(( (${INCIDENTS:-0} * 100) / $TOTAL ))
        WARNING_PCT=$(( (${WARNINGS:-0} * 100) / $TOTAL ))
        NORMAL_PCT=$(( (${NORMAL:-0} * 100) / $TOTAL ))
        
        echo "📈 DISTRIBUTION:"
        echo "   🚨 Incidents: $INCIDENT_PCT%"
        echo "   ⚠️  Warnings:  $WARNING_PCT%"  
        echo "   ℹ️  Normal:    $NORMAL_PCT%"
    fi
    
    echo ""
    echo "Press Ctrl+C to exit..."
    sleep 5
done
