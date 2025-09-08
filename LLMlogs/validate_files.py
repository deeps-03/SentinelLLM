#!/usr/bin/env python3
"""
Validation script to check that all Loki integration files have content
"""

import os
import sys

def check_file_content(filepath):
    """Check if file exists and has content"""
    if not os.path.exists(filepath):
        return False, "File does not exist"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return False, "File is empty"
            return True, f"File has {len(content)} characters"
    except Exception as e:
        return False, f"Error reading file: {e}"

def main():
    """Main validation function"""
    files_to_check = [
        'loki-config.yml',
        'promtail-config.yml', 
        'loki_kafka_forwarder.py',
        'aws_log_poller_loki.py',
        'load_test_loki_kafka.py',
        'k8s-loki-deployment.yml',
        'alertmanager.yml',
        'prometheus-alert-rules.yml',
        'LOKI_DEPLOYMENT_GUIDE.md'
    ]
    
    print("Validating Loki integration files...")
    print("=" * 50)
    
    all_good = True
    
    for filename in files_to_check:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        exists, message = check_file_content(filepath)
        
        status = "✅ PASS" if exists else "❌ FAIL"
        print(f"{status} {filename:<30} - {message}")
        
        if not exists:
            all_good = False
    
    print("=" * 50)
    
    if all_good:
        print("✅ All files validated successfully!")
        print("\nYou can now deploy the Loki integration using:")
        print("docker-compose --profile aws-loki up -d --build")
        return 0
    else:
        print("❌ Some files are missing or empty!")
        print("Please check the failed files above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
