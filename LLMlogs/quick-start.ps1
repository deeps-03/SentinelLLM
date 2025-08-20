# SentinelLLM Quick Start Script for PowerShell
# This script helps you get started with SentinelLLM quickly

param(
    [Parameter(Position=0)]
    [string]$Profile = ""
)

Write-Host "🚀 SentinelLLM Quick Start" -ForegroundColor Green
Write-Host "=========================="

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Please start Docker and try again." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is available
try {
    docker-compose --version | Out-Null
} catch {
    Write-Host "❌ Docker Compose is not installed. Please install Docker Compose and try again." -ForegroundColor Red
    exit 1
}

# Create .env file if it doesn't exist
if (!(Test-Path .env)) {
    Write-Host "📝 Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "✅ .env file created. Please edit it with your configuration before running services." -ForegroundColor Green
    
    # Check if GEMINI_API_KEY is set
    $envContent = Get-Content .env -Raw
    if ($envContent -match "GEMINI_API_KEY=your-google-gemini-api-key-here") {
        Write-Host "⚠️  Please set your GEMINI_API_KEY in the .env file before continuing." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "📄 Found existing .env file" -ForegroundColor Blue
}

# Function to show available profiles
function Show-Profiles {
    Write-Host ""
    Write-Host "🎯 Available deployment profiles:" -ForegroundColor Cyan
    Write-Host "1. basic     - Core services only (local log generation)"
    Write-Host "2. aws       - Core + AWS CloudWatch integration"
    Write-Host "3. azure     - Core + Azure Monitor integration" 
    Write-Host "4. full      - All services (AWS + Azure + notifications)"
    Write-Host ""
}

# Get deployment choice
if ($Profile -eq "") {
    Show-Profiles
    $choice = Read-Host "Choose deployment profile (1-4)"
} else {
    $choice = $Profile
}

# Set docker-compose command based on choice
switch ($choice) {
    { $_ -in "1", "basic" } {
        Write-Host "🔄 Starting basic services..." -ForegroundColor Blue
        $composeCmd = "docker-compose up -d --build"
    }
    { $_ -in "2", "aws" } {
        Write-Host "🔄 Starting services with AWS integration..." -ForegroundColor Blue
        $composeCmd = "docker-compose --profile aws up -d --build"
    }
    { $_ -in "3", "azure" } {
        Write-Host "🔄 Starting services with Azure integration..." -ForegroundColor Blue
        $composeCmd = "docker-compose --profile azure up -d --build"
    }
    { $_ -in "4", "full" } {
        Write-Host "🔄 Starting all services..." -ForegroundColor Blue
        $composeCmd = "docker-compose --profile aws --profile azure up -d --build"
    }
    default {
        Write-Host "❌ Invalid choice. Please run the script again." -ForegroundColor Red
        exit 1
    }
}

# Execute the docker-compose command
Write-Host "⏳ Building and starting services..." -ForegroundColor Yellow
Invoke-Expression $composeCmd

# Wait a moment for services to start
Start-Sleep 5

Write-Host ""
Write-Host "✅ SentinelLLM is starting up!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Access points:" -ForegroundColor Cyan
Write-Host "- Grafana: http://localhost:3000 (admin/admin)"
Write-Host "- VictoriaMetrics: http://localhost:8428"
Write-Host ""
Write-Host "🔍 Monitor logs:" -ForegroundColor Cyan
Write-Host "docker-compose logs -f log-consumer"
Write-Host "docker-compose logs -f notifier"
Write-Host ""
Write-Host "⏹️  Stop services:" -ForegroundColor Cyan
Write-Host "docker-compose down"
Write-Host ""

# Check service status
Write-Host "📋 Service status:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "🎉 Setup complete! Check the logs to verify everything is working correctly." -ForegroundColor Green
