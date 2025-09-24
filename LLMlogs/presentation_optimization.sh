#!/bin/bash

# Presentation System Optimization Script
# Reduces laptop heating and optimizes for demo

echo "🔥 Presentation System Optimization"
echo "=================================="

# Stop all containers
echo "🛑 Stopping all Docker containers..."
docker stop $(docker ps -q) 2>/dev/null || echo "No containers running"

# Clean up unused Docker resources
echo "🧹 Cleaning up Docker resources..."
docker system prune -f
docker volume prune -f
docker network prune -f

# Remove unnecessary Docker images (keep only essential ones)
echo "🗑️  Removing unused Docker images..."
docker image prune -a -f

# Show system resource usage
echo ""
echo "📊 Current System Resources:"
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | awk '{print $2 $3}' | sed 's/%us,//g'

echo "Memory Usage:"
free -h | awk 'NR==2{printf "Used: %s/%s (%.2f%%)\n", $3,$2,$3*100/$2 }'

echo "Disk Usage:"
df -h / | awk 'NR==2{printf "Used: %s/%s (%s)\n", $3,$2,$5}'

echo "Temperature (if available):"
sensors 2>/dev/null | grep -E "Core|temp" || echo "Temperature sensors not available"

# Kill unnecessary processes
echo ""
echo "🚀 Optimizing for presentation..."
sudo pkill -f "gnome-software" 2>/dev/null || true
sudo pkill -f "update-manager" 2>/dev/null || true
sudo pkill -f "snapd" 2>/dev/null || true

echo ""
echo "✅ System optimized for presentation!"
echo "💡 Now run specific demo scripts:"
echo "   ./demo_loki_integration.sh"
echo "   ./demo_patch_analyzer.sh"
echo "   ./demo_metrics_visualization.sh"