# SentinelLLM Loki Integration - Complete Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Loki integration with SentinelLLM to handle high-volume log bursts (10,000+ events/second) with intelligent buffering and auto-scaling.

## Architecture Summary

```
AWS/Azure Logs → Loki (Buffer) → Kafka → XGBoost+Qwen → VictoriaMetrics → Grafana
```

**Key Components:**
- **Loki**: High-throughput log aggregation and buffering
- **Loki-Kafka Forwarder**: Intelligent batching service with rate limiting
- **Promtail**: Multi-source log collection
- **Auto-scaling**: Kubernetes HPA for handling traffic spikes

## Prerequisites

### System Requirements
- **Minimum**: 16GB RAM, 8 CPU cores, 100GB storage
- **Recommended for production**: 32GB RAM, 16 CPU cores, 500GB SSD storage
- **Operating System**: Linux (Ubuntu 20.04+, CentOS 8+) or Windows 10/11 with WSL2

### Software Dependencies
- Docker 20.10+ and Docker Compose 2.0+
- Kubernetes 1.21+ (for production scaling)
- Python 3.9+
- Git

### Network Requirements
- Port 3100: Loki HTTP API
- Port 9080: Promtail
- Port 9092: Kafka
- Port 8428: VictoriaMetrics
- Port 3000: Grafana

## Deployment Options

### Option 1: Docker Compose (Development/Testing)

#### 1. Clone and Prepare Repository
```bash
git clone <repository-url>
cd SentinelLLM/LLMlogs
```

#### 2. Environment Configuration
Create `.env` file:
```bash
# Loki Configuration
LOKI_RETENTION_PERIOD=168h
LOKI_MAX_INGESTION_RATE=100MB
LOKI_MAX_STREAMS=50000

# Kafka Configuration
KAFKA_PARTITIONS=12
KAFKA_REPLICATION_FACTOR=3

# AWS Configuration (if using AWS logs)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Azure Configuration (if using Azure logs)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

#### 3. Deploy with Loki Integration
```bash
# Build and start all services
docker compose --profile aws-loki up -d --build

# Check service health
docker compose ps

# View logs
docker compose logs -f loki
docker compose logs -f loki-kafka-forwarder
```

#### 4. Verify Deployment
```bash
# Test Loki endpoint
curl http://localhost:3100/ready

# Test log ingestion
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H "Content-Type: application/json" \
  -d '{"streams":[{"stream":{"source":"test"},"values":[["1640995200000000000","test log message"]]}]}'

# Check Kafka topics
docker exec -it kafka kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Option 2: Kubernetes (Production)

#### 1. Prepare Kubernetes Cluster
```bash
# Ensure cluster has sufficient resources
kubectl get nodes

# Create namespace
kubectl create namespace sentinellm

# Create persistent volumes (adjust paths for your environment)
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: loki-storage
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  local:
    path: /opt/loki-data
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - your-node-name
EOF
```

#### 2. Deploy to Kubernetes
```bash
# Apply the complete deployment
kubectl apply -f k8s-loki-deployment.yml -n sentinellm

# Monitor deployment progress
kubectl get pods -n sentinellm -w

# Check HPA status
kubectl get hpa -n sentinellm
```

#### 3. Configure Ingress (Optional)
```bash
# Create ingress for external access
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sentinellm-ingress
  namespace: sentinellm
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: sentinellm.your-domain.com
    http:
      paths:
      - path: /loki
        pathType: Prefix
        backend:
          service:
            name: loki
            port:
              number: 3100
      - path: /grafana
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 3000
EOF
```

## Configuration Tuning

### High-Volume Optimization

#### Loki Configuration (`loki-config.yml`)
Key settings for 10,000+ events/sec:
```yaml
ingester:
  chunk_target_size: 2097152  # 2MB chunks
  max_chunk_age: 1h
  concurrent_flushes: 16
  
limits_config:
  ingestion_rate_mb: 100       # 100MB/s ingestion
  ingestion_burst_size_mb: 200 # 200MB burst
  max_streams_per_user: 50000  # High stream count
```

#### Kafka Optimization
```yaml
# In docker compose.yml or Kubernetes deployment
environment:
  KAFKA_NUM_PARTITIONS: 12
  KAFKA_DEFAULT_REPLICATION_FACTOR: 3
  KAFKA_LOG_RETENTION_HOURS: 168
  KAFKA_LOG_SEGMENT_BYTES: 1073741824  # 1GB segments
```

### Auto-Scaling Configuration

#### HPA Thresholds (Kubernetes)
```yaml
# Adjust in k8s-loki-deployment.yml
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 70
- type: Resource
  resource:
    name: memory
    target:
      type: Utilization
      averageUtilization: 80
```

## Monitoring Setup

### 1. Import Grafana Dashboard
```bash
# Access Grafana (default: admin/admin)
http://localhost:3000

# Import dashboard from grafana-loki-performance-dashboard.json
# Navigate to: Dashboards → Import → Upload JSON file
```

### 2. Configure Alerts
```bash
# Prometheus alerts are automatically loaded from prometheus-alert-rules.yml
# Configure AlertManager notifications in alertmanager.yml

# Test alerts
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{"labels":{"alertname":"test","severity":"warning"}}]'
```

### 3. Health Checks
Key endpoints to monitor:
- Loki: `http://localhost:3100/ready`
- Prometheus: `http://localhost:9090/targets`
- Grafana: `http://localhost:3000/api/health`
- Kafka: Check topic lag via JMX metrics

## Load Testing

### Run Performance Tests
```bash
# Install dependencies
pip install aiohttp kafka-python

# Basic load test
python load_test_loki_kafka.py --rate 5000 --duration 300 --clients 25

# High-volume test
python load_test_loki_kafka.py --rate 15000 --duration 600 --clients 50 --batch-size 200

# Save detailed results
python load_test_loki_kafka.py --rate 10000 --duration 300 --output test_results.json
```

### Expected Performance
- **Target**: 10,000+ events/second sustained
- **Burst handling**: Up to 20,000 events/second for 10 minutes
- **Latency**: <2 seconds end-to-end (log ingestion to Kafka)
- **Auto-scaling**: 3-20 replicas based on load

## Troubleshooting

### Common Issues

#### 1. High Memory Usage
```bash
# Check memory consumption
docker stats
kubectl top pods -n sentinellm

# Solutions:
# - Increase memory limits in docker compose.yml or k8s deployment
# - Reduce chunk_target_size in Loki config
# - Enable chunk compression
```

#### 2. Ingestion Rate Limits
```bash
# Check Loki logs for rate limiting
docker compose logs loki | grep "ingestion rate limit"

# Solutions:
# - Increase ingestion_rate_mb in loki-config.yml
# - Scale Loki horizontally (Kubernetes)
# - Optimize batch sizes in forwarder
```

#### 3. Kafka Consumer Lag
```bash
# Check consumer lag
docker exec -it kafka kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --all-groups

# Solutions:
# - Increase partition count
# - Scale consumer instances
# - Optimize batch processing in consumer
```

#### 4. Auto-scaling Not Triggering
```bash
# Check HPA status
kubectl describe hpa loki-forwarder-hpa -n sentinellm

# Check metrics server
kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes

# Solutions:
# - Verify metrics-server is running
# - Check custom metrics configuration
# - Adjust HPA thresholds
```

### Log Analysis Commands

```bash
# Loki query examples
curl -G 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={source="aws-cloudwatch"}' \
  --data-urlencode 'start=2024-01-01T00:00:00Z' \
  --data-urlencode 'end=2024-01-01T23:59:59Z'

# Check forwarder metrics
curl http://localhost:8080/metrics | grep loki_forwarder

# Kafka topic inspection
docker exec -it kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic raw-logs \
  --from-beginning --max-messages 10
```

## Production Checklist

### Before Deployment
- [ ] Resource requirements verified
- [ ] Network ports configured
- [ ] SSL certificates prepared (for production)
- [ ] Backup strategy defined
- [ ] Monitoring dashboards tested
- [ ] Alert notifications configured
- [ ] Load testing completed

### Security Considerations
- [ ] Change default passwords (Grafana, databases)
- [ ] Enable TLS for all services
- [ ] Configure authentication for Loki/Grafana
- [ ] Set up network policies (Kubernetes)
- [ ] Regular security updates scheduled

### Backup and Recovery
- [ ] Loki index and chunks backup
- [ ] Kafka topic backup strategy
- [ ] Configuration files versioned
- [ ] Disaster recovery procedure documented

## Performance Optimization Tips

### 1. Loki Optimization
- Use SSD storage for WAL and chunks
- Configure appropriate retention policies
- Use parallel queries for large time ranges
- Enable chunk compression for storage efficiency

### 2. Kafka Optimization
- Set appropriate partition count (CPU cores × 2-3)
- Use batch.size and linger.ms for throughput
- Monitor replication lag
- Consider separate disks for logs and data

### 3. Kubernetes Optimization
- Use node affinity for storage-heavy pods
- Configure resource limits and requests properly
- Use priority classes for critical workloads
- Monitor cluster resource utilization

## Support and Maintenance

### Regular Maintenance Tasks
- **Daily**: Check dashboard alerts, service health
- **Weekly**: Review performance metrics, clean old logs
- **Monthly**: Update configurations, security patches
- **Quarterly**: Capacity planning, disaster recovery tests

### Upgrade Procedures
1. Test upgrades in staging environment
2. Backup configurations and data
3. Follow rolling update strategy
4. Validate functionality post-upgrade
5. Monitor for 24 hours after upgrade

This comprehensive deployment guide ensures successful implementation of the Loki integration for handling high-volume log bursts with SentinelLLM.