#!/usr/bin/env python3
"""
Ultra-Fast Loki Client for Production Demo
Optimized for speed and reliability
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UltraFastLokiClient:
    """Production-ready ultra-fast Loki client"""
    
    def __init__(self, loki_url: str = "http://localhost:3100"):
        self.loki_url = loki_url
        self.push_url = f"{loki_url}/loki/api/v1/push"
        self.query_url = f"{loki_url}/loki/api/v1/query_range"
        self.instant_query_url = f"{loki_url}/loki/api/v1/query"
        
        # Ultra-performance optimizations
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,  # Connection pooling
            pool_maxsize=20,
            max_retries=1
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        # Aggressive timeouts for demo
        self.timeout = 3  # 3 seconds max
        
        # Cache for repeated queries
        self._cache = {}
        self._cache_ttl = 30  # 30 seconds cache
        
    def test_connection(self) -> bool:
        """Ultra-fast connection test"""
        try:
            response = self.session.get(f"{self.loki_url}/ready", timeout=1.0)
            is_ready = response.status_code == 200
            logger.info(f"Loki connection: {'✅ Ready' if is_ready else '❌ Not ready'}")
            return is_ready
        except Exception as e:
            logger.warning(f"❌ Connection failed: {str(e)[:50]}...")
            return False
    
    def _get_cache_key(self, query: str, start: str, end: str) -> str:
        """Generate cache key for queries"""
        return f"{query}:{start}:{end}"
    
    def _is_cache_valid(self, cache_entry) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - cache_entry['timestamp'] < self._cache_ttl
    
    def send_logs_instant(self, logs: List[Dict]) -> bool:
        """Send logs with minimal latency"""
        try:
            # Format for Loki (simplified)
            payload = {"streams": []}
            
            for log in logs:
                timestamp_ns = str(int(time.time() * 1_000_000_000))
                stream_data = {
                    "stream": {
                        "job": log.get("service", "app"),
                        "level": log.get("level", "info"),
                        "instance": log.get("host", "localhost")
                    },
                    "values": [[timestamp_ns, json.dumps(log)]]
                }
                payload["streams"].append(stream_data)
            
            response = self.session.post(
                self.push_url, 
                json=payload,
                timeout=self.timeout
            )
            
            success = response.status_code == 204
            if success:
                logger.info(f"✅ Sent {len(logs)} logs instantly")
            else:
                logger.error(f"❌ Send failed: {response.status_code}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Send error: {str(e)[:100]}...")
            return False
    
    def query_logs_instant(self, 
                          service_name: str = "app",
                          level: str = None,
                          limit: int = 100,
                          minutes_back: int = 10) -> List[Dict]:
        """Get logs instantly with caching"""
        
        # Build optimized query
        if level:
            query = f'{{job="{service_name}", level="{level}"}}'
        else:
            query = f'{{job="{service_name}"}}'
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes_back)
        
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        # Check cache first
        cache_key = self._get_cache_key(query, start_str, end_str)
        if cache_key in self._cache and self._is_cache_valid(self._cache[cache_key]):
            logger.info("⚡ Cache hit - instant response")
            return self._cache[cache_key]['data']
        
        try:
            # Optimized query parameters
            params = {
                'query': query,
                'start': start_str,
                'end': end_str,
                'limit': limit,
                'direction': 'backward'  # Get latest logs first
            }
            
            logger.info(f"🔍 Querying Loki: {service_name} (last {minutes_back}m)")
            start_query_time = time.time()
            
            response = self.session.get(
                self.query_url,
                params=params,
                timeout=self.timeout
            )
            
            query_time = time.time() - start_query_time
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse logs quickly
                logs = []
                for stream in result.get('data', {}).get('result', []):
                    for entry in stream.get('values', []):
                        if len(entry) >= 2:
                            try:
                                # Try to parse as JSON, fallback to string
                                log_data = json.loads(entry[1])
                                if isinstance(log_data, dict):
                                    logs.append(log_data)
                                else:
                                    logs.append({"message": entry[1]})
                            except json.JSONDecodeError:
                                logs.append({"message": entry[1]})
                
                # Cache the result
                self._cache[cache_key] = {
                    'data': logs,
                    'timestamp': time.time()
                }
                
                logger.info(f"✅ Retrieved {len(logs)} logs in {query_time:.2f}s")
                return logs
                
            else:
                logger.error(f"❌ Query failed: {response.status_code}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error("❌ Query timeout - Loki too slow")
            return []
        except Exception as e:
            logger.error(f"❌ Query error: {str(e)[:100]}...")
            return []
    
    def get_recent_anomalies(self, minutes_back: int = 30) -> List[Dict]:
        """Get recent anomaly logs for demo"""
        anomaly_logs = []
        
        # Query error logs
        error_logs = self.query_logs_instant("app", "error", limit=50, minutes_back=minutes_back)
        anomaly_logs.extend([{"type": "error", **log} for log in error_logs])
        
        # Query warning logs
        warning_logs = self.query_logs_instant("app", "warning", limit=50, minutes_back=minutes_back)
        anomaly_logs.extend([{"type": "warning", **log} for log in warning_logs])
        
        # Sort by timestamp if available
        try:
            anomaly_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        except:
            pass
        
        logger.info(f"📊 Found {len(anomaly_logs)} anomalies in last {minutes_back} minutes")
        return anomaly_logs[:100]  # Limit for demo
    
    def health_check(self) -> Dict[str, str]:
        """Quick system health check for demo"""
        try:
            start_time = time.time()
            
            # Test connection
            connection_ok = self.test_connection()
            
            # Quick query test
            test_logs = self.query_logs_instant("app", limit=1, minutes_back=1)
            query_ok = isinstance(test_logs, list)
            
            response_time = time.time() - start_time
            
            status = "✅ Healthy" if (connection_ok and query_ok) else "❌ Issues"
            
            return {
                "status": status,
                "connection": "✅ OK" if connection_ok else "❌ Failed",
                "query": "✅ OK" if query_ok else "❌ Failed", 
                "response_time": f"{response_time:.2f}s",
                "cache_entries": len(self._cache)
            }
            
        except Exception as e:
            return {
                "status": "❌ Error",
                "error": str(e)[:100],
                "response_time": "N/A"
            }


def demo_loki_performance():
    """Demo function to show Loki performance"""
    print("🚀 Starting Ultra-Fast Loki Demo")
    print("=" * 50)
    
    # Initialize client
    client = UltraFastLokiClient()
    
    # Health check
    print("1. Health Check:")
    health = client.health_check()
    for key, value in health.items():
        print(f"   {key}: {value}")
    
    print("\n2. Sending Sample Logs:")
    # Send some sample logs
    sample_logs = [
        {"level": "info", "message": "Application started", "service": "app"},
        {"level": "warning", "message": "High CPU usage detected", "service": "app"},
        {"level": "error", "message": "Database connection failed", "service": "app"},
        {"level": "info", "message": "User login successful", "service": "app"},
    ]
    
    if client.send_logs_instant(sample_logs):
        print("   ✅ Sample logs sent successfully")
    else:
        print("   ❌ Failed to send logs")
    
    # Small delay for logs to be indexed
    time.sleep(1)
    
    print("\n3. Retrieving Recent Logs:")
    logs = client.query_logs_instant("app", limit=10, minutes_back=5)
    print(f"   Retrieved: {len(logs)} logs")
    for i, log in enumerate(logs[:3]):  # Show first 3
        message = log.get('message', str(log))[:60]
        print(f"   {i+1}. {message}...")
    
    print("\n4. Finding Anomalies:")
    anomalies = client.get_recent_anomalies(minutes_back=5)
    print(f"   Found: {len(anomalies)} anomalies")
    for i, anomaly in enumerate(anomalies[:2]):  # Show first 2
        anom_type = anomaly.get('type', 'unknown')
        message = anomaly.get('message', str(anomaly))[:50]
        print(f"   {i+1}. [{anom_type}] {message}...")
    
    print("\n" + "=" * 50)
    print("🎯 Demo Complete - System Ready!")


if __name__ == "__main__":
    demo_loki_performance()