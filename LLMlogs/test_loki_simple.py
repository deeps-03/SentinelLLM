import requests
import json
import time
from datetime import datetime

def test_loki_integration():
    """Test basic Loki integration by sending sample logs"""
    
    loki_url = "http://localhost:3100/loki/api/v1/push"
    
    # Sample log entry
    timestamp_ns = str(int(time.time() * 1000000000))  # nanoseconds
    
    payload = {
        "streams": [
            {
                "stream": {
                    "job": "sentinellm-test",
                    "level": "info",
                    "service": "loki-integration-test"
                },
                "values": [
                    [timestamp_ns, "Test log message from SentinelLLM - Loki integration working!"]
                ]
            }
        ]
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"🔄 Testing Loki integration at {loki_url}")
        response = requests.post(loki_url, data=json.dumps(payload), headers=headers)
        
        if response.status_code == 204:
            print("✅ SUCCESS: Log sent to Loki successfully!")
            print(f"   Status Code: {response.status_code}")
            print(f"   Timestamp: {datetime.now()}")
            
            # Test querying the log back
            print("\n🔄 Testing log retrieval...")
            query_url = "http://localhost:3100/loki/api/v1/query_range"
            params = {
                'query': '{job="sentinellm-test"}',
                'start': str(int((time.time() - 60) * 1000000000)),  # 1 minute ago
                'end': str(int(time.time() * 1000000000)),
                'limit': 10
            }
            
            query_response = requests.get(query_url, params=params)
            if query_response.status_code == 200:
                result = query_response.json()
                if result.get('data', {}).get('result'):
                    print("✅ SUCCESS: Log retrieved from Loki successfully!")
                    print(f"   Found {len(result['data']['result'])} log streams")
                    for stream in result['data']['result']:
                        print(f"   Stream labels: {stream['stream']}")
                        print(f"   Values count: {len(stream['values'])}")
                else:
                    print("⚠️  WARNING: No logs found in query result")
            else:
                print(f"❌ ERROR: Failed to query logs - Status: {query_response.status_code}")
                
        else:
            print(f"❌ ERROR: Failed to send log to Loki")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to Loki. Make sure it's running on localhost:3100")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    test_loki_integration()
