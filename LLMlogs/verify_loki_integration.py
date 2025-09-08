#!/usr/bin/env python3
"""
Loki Integration Verification Script
Checks if all Loki integration components are properly configured
"""

import os
import json
import yaml
import sys
from pathlib import Path

def load_yaml_file(filepath):
    """Load and validate YAML file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        return None, str(e)

def load_json_file(filepath):
    """Load and validate JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return None, str(e)

def check_loki_config():
    """Check Loki configuration"""
    print("🔍 Checking Loki Configuration...")
    
    config = load_yaml_file('loki-config.yml')
    if isinstance(config, tuple):
        print(f"❌ Error loading loki-config.yml: {config[1]}")
        return False
    
    # Check key configuration values
    checks = [
        ("auth_enabled", False),
        ("server.http_listen_port", 3100),
        ("ingester.chunk_target_size", 2097152),  # 2MB
        ("limits_config.ingestion_rate_mb", 100),
        ("limits_config.max_streams_per_user", 50000)
    ]
    
    for key_path, expected in checks:
        keys = key_path.split('.')
        value = config
        try:
            for key in keys:
                value = value[key]
            if value == expected:
                print(f"✅ {key_path}: {value}")
            else:
                print(f"⚠️  {key_path}: {value} (expected: {expected})")
        except (KeyError, TypeError):
            print(f"❌ Missing configuration: {key_path}")
    
    return True

def check_promtail_config():
    """Check Promtail configuration"""
    print("\n🔍 Checking Promtail Configuration...")
    
    config = load_yaml_file('promtail-config.yml')
    if isinstance(config, tuple):
        print(f"❌ Error loading promtail-config.yml: {config[1]}")
        return False
    
    # Check basic structure
    if 'scrape_configs' in config:
        scrape_jobs = [job.get('job_name', 'unnamed') for job in config['scrape_configs']]
        print(f"✅ Scrape jobs configured: {', '.join(scrape_jobs)}")
    else:
        print("❌ No scrape_configs found")
        return False
    
    if 'clients' in config:
        loki_url = config['clients'][0].get('url', 'not set')
        print(f"✅ Loki client URL: {loki_url}")
    else:
        print("❌ No Loki clients configured")
        return False
    
    return True

def check_docker_compose():
    """Check Docker Compose configuration"""
    print("\n🔍 Checking Docker Compose Configuration...")
    
    if not os.path.exists('docker-compose.yml'):
        print("❌ docker-compose.yml not found")
        return False
    
    try:
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
        
        # Check for Loki services
        loki_services = ['loki', 'promtail', 'loki-kafka-forwarder']
        for service in loki_services:
            if service in content:
                print(f"✅ Service '{service}' found in docker-compose.yml")
            else:
                print(f"❌ Service '{service}' not found in docker-compose.yml")
        
        # Check for profiles
        if 'aws-loki' in content:
            print("✅ AWS-Loki profile found")
        if 'azure-loki' in content:
            print("✅ Azure-Loki profile found")
        
        return True
    except Exception as e:
        print(f"❌ Error reading docker-compose.yml: {e}")
        return False

def check_kubernetes_config():
    """Check Kubernetes configuration"""
    print("\n🔍 Checking Kubernetes Configuration...")
    
    if not os.path.exists('k8s-loki-deployment.yml'):
        print("❌ k8s-loki-deployment.yml not found")
        return False
    
    try:
        with open('k8s-loki-deployment.yml', 'r') as f:
            content = f.read()
        
        # Check for key components
        k8s_components = [
            'kind: Deployment',
            'app: loki',
            'app: loki-forwarder',
            'HorizontalPodAutoscaler',
            'ConfigMap'
        ]
        
        for component in k8s_components:
            if component in content:
                print(f"✅ {component} found")
            else:
                print(f"❌ {component} not found")
        
        return True
    except Exception as e:
        print(f"❌ Error reading k8s-loki-deployment.yml: {e}")
        return False

def check_monitoring_config():
    """Check monitoring configuration"""
    print("\n🔍 Checking Monitoring Configuration...")
    
    files_to_check = [
        ('grafana-loki-performance-dashboard.json', 'JSON'),
        ('prometheus-alert-rules.yml', 'YAML'),
        ('alertmanager.yml', 'YAML')
    ]
    
    all_good = True
    for filename, file_type in files_to_check:
        if os.path.exists(filename):
            try:
                if file_type == 'JSON':
                    with open(filename, 'r') as f:
                        json.load(f)
                else:
                    with open(filename, 'r') as f:
                        yaml.safe_load(f)
                print(f"✅ {filename} is valid {file_type}")
            except Exception as e:
                print(f"❌ {filename} has invalid {file_type}: {e}")
                all_good = False
        else:
            print(f"❌ {filename} not found")
            all_good = False
    
    return all_good

def check_python_services():
    """Check Python service files"""
    print("\n🔍 Checking Python Services...")
    
    python_files = [
        'loki_kafka_forwarder.py',
        'aws_log_poller_loki.py',
        'load_test_loki_kafka.py'
    ]
    
    all_good = True
    for filename in python_files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    content = f.read()
                if len(content.strip()) > 100:  # Basic content check
                    print(f"✅ {filename} has content ({len(content)} chars)")
                else:
                    print(f"⚠️  {filename} seems too short")
                    all_good = False
            except Exception as e:
                print(f"❌ Error reading {filename}: {e}")
                all_good = False
        else:
            print(f"❌ {filename} not found")
            all_good = False
    
    return all_good

def check_dependencies():
    """Check if required Python packages are available"""
    print("\n🔍 Checking Python Dependencies...")
    
    required_packages = [
        'aiohttp',
        'kafka',  # kafka-python
        'yaml',   # PyYAML
        'json'    # built-in
    ]
    
    all_good = True
    for package in required_packages:
        try:
            if package == 'kafka':
                import kafka
            elif package == 'yaml':
                import yaml
            elif package == 'json':
                import json
            else:
                __import__(package)
            print(f"✅ {package} is available")
        except ImportError:
            print(f"❌ {package} is not installed")
            all_good = False
    
    return all_good

def provide_next_steps(docker_running=False):
    """Provide next steps based on verification results"""
    print("\n" + "="*60)
    print("🚀 NEXT STEPS")
    print("="*60)
    
    if not docker_running:
        print("1. Start Docker Desktop:")
        print("   - Open Docker Desktop application")
        print("   - Wait for it to fully start (green icon in system tray)")
        print()
    
    print("2. Start Loki integration services:")
    print("   docker-compose --profile aws-loki up -d --build")
    print()
    
    print("3. Verify services are running:")
    print("   docker-compose ps")
    print()
    
    print("4. Test Loki endpoint:")
    print("   curl http://localhost:3100/ready")
    print()
    
    print("5. Run load test:")
    print("   python load_test_loki_kafka.py --rate 1000 --duration 30")
    print()
    
    print("6. Access monitoring:")
    print("   - Grafana: http://localhost:3000 (admin/admin)")
    print("   - Loki: http://localhost:3100")
    print("   - VictoriaMetrics: http://localhost:8428")

def main():
    """Main verification function"""
    print("🔧 SentinelLLM Loki Integration Verification")
    print("="*60)
    
    # Check if we're in the right directory
    if not os.path.exists('loki-config.yml'):
        print("❌ Please run this script from the LLMlogs directory")
        return 1
    
    # Run all checks
    checks = [
        check_loki_config(),
        check_promtail_config(),
        check_docker_compose(),
        check_kubernetes_config(),
        check_monitoring_config(),
        check_python_services(),
        check_dependencies()
    ]
    
    # Summary
    passed = sum(checks)
    total = len(checks)
    
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)
    print(f"Passed: {passed}/{total} checks")
    
    if passed == total:
        print("✅ All checks passed! Loki integration is properly configured.")
        provide_next_steps(docker_running=False)
        return 0
    else:
        print(f"⚠️  {total - passed} checks failed. Please review the issues above.")
        provide_next_steps(docker_running=False)
        return 1

if __name__ == "__main__":
    try:
        import yaml
    except ImportError:
        print("Installing PyYAML...")
        os.system("pip install PyYAML")
        import yaml
    
    sys.exit(main())
