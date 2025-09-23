#!/bin/bash

# Grafana API Key Setup Script
# This script helps you create an API key for programmatic access to Grafana

echo "🔑 Grafana API Key Setup"
echo "========================"

GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASS="admin"

echo "📋 Grafana Configuration:"
echo "URL: $GRAFANA_URL"
echo "Username: $GRAFANA_USER"
echo ""

# Wait for Grafana to be ready
echo "⏳ Waiting for Grafana to be ready..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -s "$GRAFANA_URL/api/health" > /dev/null 2>&1; then
        echo "✅ Grafana is ready!"
        break
    fi
    retry_count=$((retry_count + 1))
    echo "⏳ Waiting... ($retry_count/$max_retries)"
    sleep 2
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ Grafana did not become ready in time"
    exit 1
fi

# Create API key
echo ""
echo "🔐 Creating API key..."

API_KEY_RESPONSE=$(curl -s -X POST \
  "$GRAFANA_URL/api/auth/keys" \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASS" \
  -d '{
    "name": "SentinelLLM-API-Key",
    "role": "Admin"
  }')

if echo "$API_KEY_RESPONSE" | grep -q '"key"'; then
    API_KEY=$(echo "$API_KEY_RESPONSE" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)
    echo "✅ API Key created successfully!"
    echo ""
    echo "🔑 Your Grafana API Key:"
    echo "========================"
    echo "$API_KEY"
    echo ""
    echo "💾 Save this key securely - it won't be shown again!"
    echo ""
    
    # Save to .env file
    ENV_FILE="/home/indresh/SentinelLLM/LLMlogs/.env"
    if [ -f "$ENV_FILE" ]; then
        if grep -q "GRAFANA_API_KEY=" "$ENV_FILE"; then
            # Update existing entry
            sed -i "s/GRAFANA_API_KEY=.*/GRAFANA_API_KEY=$API_KEY/" "$ENV_FILE"
        else
            # Add new entry
            echo "GRAFANA_API_KEY=$API_KEY" >> "$ENV_FILE"
        fi
        echo "✅ API Key saved to .env file"
    fi
    
    echo ""
    echo "📊 Test the API key:"
    echo "curl -H \"Authorization: Bearer $API_KEY\" $GRAFANA_URL/api/dashboards/home"
    
else
    echo "❌ Failed to create API key"
    echo "Response: $API_KEY_RESPONSE"
    
    if echo "$API_KEY_RESPONSE" | grep -q "401"; then
        echo ""
        echo "💡 This might be because you changed the default password."
        echo "Please update GRAFANA_PASS variable in this script with your new password."
    fi
fi