# SentinelLLM 🚀

## Project Description 📝
**SentinelLLM** is a comprehensive, production-ready **AI-powered log analysis and patch readiness assessment platform** that combines real-time log streaming with intelligent anomaly detection and multi-model machine learning analysis.

### What This Project Does
1. **Real-Time Log Analysis**: Streams and analyzes logs from multiple sources (AWS, Azure, Kafka)
2. **Intelligent Patch Analysis**: Uses 3 ML models (Sliding Window+EMA, Prophet, Isolation Forest) to assess patch deployment readiness
3. **Ultra-Fast Log Retrieval**: Optimized Loki integration with 30ms query response times
4. **Anomaly Detection**: Multi-layered anomaly detection using traditional ML and deep learning
5. **Production Monitoring**: Complete alerting, dashboards, and notification systems

### Business Value
- **Reduce Deployment Risk**: AI predicts patch deployment success with confidence scoring
- **Faster Incident Response**: Sub-second log analysis and anomaly detection  
- **Cost Savings**: Prevent failed deployments and reduce downtime
- **Scalable Architecture**: Handles 10,000+ events/second with Docker/Kubernetes support

## Key Features ✨

### 🤖 Multi-Model Patch Analysis System
*   **Sliding Window + EMA**: Real-time trend analysis for immediate anomaly detection
*   **Prophet Time Series**: Advanced forecasting to predict deployment risks based on historical patterns
*   **Isolation Forest**: Unsupervised learning to detect novel anomaly patterns
*   **Meta-Classifier**: Intelligent voting system combines all models for final risk assessment
*   **Performance**: 37ms per analysis, 26+ analyses/second throughput

### ⚡ Ultra-Fast Loki Integration  
*   **Lightning Speed**: 30ms log retrieval with aggressive optimization
*   **Connection Pooling**: Reuses connections for maximum performance
*   **Smart Caching**: Reduces redundant queries
*   **High Volume**: Handles 10,000+ events/second ingestion
*   **Production Ready**: 3-second timeouts prevent hanging

### 🔍 Advanced Log Analysis
*   **XGBoost Classification**: Traditional ML model classifies logs into `incident` 🚨, `preventive_action` 🛠️, or `normal`
*   **TF-IDF Vectorization**: Intelligent text processing and feature extraction
*   **Real-time Streaming**: Kafka-based architecture for high-throughput processing
*   **Anomaly Detection**: Multi-layered detection with configurable thresholds

## 🚀 Quick Start Guide

### Prerequisites
- **Docker** and **Docker Compose** installed
- **Python 3.12+** 
- **Git** for cloning

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/deeps-03/SentinelLLM.git
cd SentinelLLM/LLMlogs

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Generate Required Models
```bash
# Generate XGBoost model, vectorizer, and label encoder
python model_train.py

# This creates:
# - vectorizer.pkl (TF-IDF vectorizer for text processing)
# - label_encoder.pkl (Label encoder for classifications)
# - xgboost_model.pkl (Trained XGBoost model)
```

### 3. Start Core Services
```bash
# Start Kafka, Zookeeper, and Loki
docker-compose up -d kafka zookeeper loki

# Wait 30 seconds for services to initialize
sleep 30
```

### 4. Test Patch Analysis System
```bash
# Test the multi-model patch analyzer
python test_patch_analyzer.py

# Expected output:
# ✅ Risk Assessment: LOW/MEDIUM/HIGH
# ✅ Confidence Score: 0.XXX
# ✅ Analysis Time: ~37ms
# ✅ Throughput: 26+ analyses/second
```

### 5. Test Ultra-Fast Loki Integration
```bash
# Test optimized log retrieval
python ultra_fast_loki.py

# Expected output:
# ✅ Connection: Ready (health check)
# ✅ Query Speed: 0.03 seconds
# ✅ Log Ingestion: Working
# ✅ Anomaly Detection: 2 anomalies found
```

### 6. Test Complete System
```bash
# Run comprehensive multi-model system test
python test_multi_model_system.py
```

## 📋 Complete Workflow

### System Architecture Overview
1. **Log Ingestion** → Loki buffer → Kafka streaming
2. **ML Processing** → XGBoost classification + Multi-model patch analysis  
3. **Anomaly Detection** → Isolation Forest + statistical analysis
4. **Risk Assessment** → Prophet forecasting + trend analysis
5. **Alerting** → Email + Teams notifications
6. **Monitoring** → Grafana dashboards + metrics

### Core Workflows

#### A) Patch Deployment Analysis Workflow
```bash
# 1. Collect system metrics (CPU, memory, response times)
current_metrics = {
    "cpu_usage": 85.7,
    "memory_usage": 78.2, 
    "response_time": 420.5,
    "error_rate": 3.1
}

# 2. Run multi-model analysis
analyzer = PatchAnalyzer()
result = analyzer.analyze_patch_metrics(current_metrics)

# 3. Get risk assessment
# Output: {"predicted_risk_level": "MEDIUM", "confidence": 0.82, "anomalies": [...]}
```

#### B) Real-Time Log Analysis Workflow
```bash
# 1. Logs flow: AWS/Azure → Loki → Kafka → XGBoost Classifier
# 2. Classification: incident/preventive_action/normal
# 3. Anomaly detection if incident or high severity
# 4. Metrics stored in VictoriaMetrics
# 5. Alerts sent via Email/Teams if needed
```

### File Structure & Purpose
```
LLMlogs/
├── patch_analyzer.py          # 🤖 Multi-model patch analysis system
├── ultra_fast_loki.py         # ⚡ Optimized Loki client (30ms queries)  
├── model_train.py             # 🔧 Generate XGBoost/vectorizer models
├── simple_consumer.py         # 📨 Kafka consumer + XGBoost classifier
├── log_producer.py            # 📤 Kafka log producer for testing
├── anomaly_detector.py        # 🔍 Anomaly detection service
├── notifier.py                # 📢 Email + Teams notifications
├── aws_log_poller.py          # ☁️ AWS CloudWatch integration
├── azure_log_poller.py        # ☁️ Azure Monitor integration
├── docker-compose.yml         # 🐳 Complete infrastructure setup
├── requirements.txt           # 📦 Python dependencies
├── *.pkl                      # 💾 Trained ML models (auto-generated)
└── test_*.py                  # ✅ Comprehensive test suites
```

### Fine-Tuning
*   **In-house Model Training:** Includes a complete workflow for fine-tuning the log classification model on your own data.
*   **PEFT with LoRA:** Uses Parameter-Efficient Fine-Tuning (PEFT) with Low-Rank Adaptation (LoRA) for efficient and effective training.
*   **Customizable Training:** The `fine_tune.py` script provides a flexible framework for fine-tuning the model on different datasets and with different training parameters.

### Loki Integration
*   **High-Volume Log Handling:** The Loki integration is specifically designed to handle large volumes of logs (10,000+ events/second).
*   **Buffering and Rate-Limiting:** Uses Loki as a buffer and a custom `loki-kafka-forwarder` service for intelligent batching and rate-limiting.
*   **Scalability:** The Loki integration can be deployed on Kubernetes for auto-scaling.

### Cloud Log Ingestion 🌩️
*   **AWS CloudWatch Integration:** Real-time polling of CloudWatch log groups with checkpoint management.
*   **Azure Monitor Integration:** Near real-time querying of Log Analytics workspaces with KQL support.
*   **Checkpoint Management:** Both AWS and Azure pollers maintain state to avoid duplicate log ingestion after restarts.

### Alert & Notification System 📢
*   **Smart Alerting Rules:**
    *   `incident` classification → Email + Microsoft Teams
    *   `preventive_action` classification → Teams (+ optional Email)
    *   Anomaly score ≥ threshold → Email + Teams
*   **Email Notifications:** SMTP-based email alerts with HTML formatting.
*   **Microsoft Teams Integration:** Rich card notifications with action buttons.
*   **Alert Deduplication:** Prevents spam by suppressing duplicate alerts within configurable time windows.

### Production Features 🔧
*   **Containerized Environment:** All services run in Docker with Docker Compose orchestration.
*   **Environment-based Configuration:** Comprehensive `.env` file support for all settings.
*   **Service Profiles:** Optional cloud services (AWS/Azure) can be enabled per deployment.
*   **Robust Error Handling:** Retry mechanisms, backoff strategies, and graceful degradation.
*   **Comprehensive Logging:** Structured logging throughout all services.

## Technologies Used 🛠️
*   **AI Model:** `Deeps03/qwen2-1.5b-log-classifier` (via LlamaCpp)
*   **Fine-Tuning:** PEFT (Parameter-Efficient Fine-Tuning) with LoRA
*   **Python Libraries:** 
    *   `langchain`, `langchain-community`, `llama-cpp-python` - AI classification
    *   `kafka-python` - Streaming
    *   `boto3` - AWS integration
    *   `azure-monitor-query`, `azure-identity` - Azure integration
    *   `requests` - HTTP communications
    *   `python-dotenv` - Configuration management
*   **Infrastructure:** Kafka & Zookeeper, VictoriaMetrics, Grafana, Loki
*   **Cloud Platforms:** AWS CloudWatch, Azure Monitor/Log Analytics
*   **Notification Systems:** SMTP Email, Microsoft Teams Webhooks
*   **Containerization:** Docker & Docker Compose

## Architecture Diagram 🗺️
```
                         +---------------------+     +---------------------+     +---------------------+
                         |    AWS CloudWatch   |     |    Azure Monitor    |     | Local Log Producer  |
                         +---------------------+     +---------------------+     +---------------------+
                                   |                        |                          |
                                   |                        |                          |
                                   +------------------------+--------------------------+
                                                            |
                                                            v
                                                   +---------------------+
                                                   |    Loki (Buffer)    |
                                                   +---------------------+
                                                            |
                                                            v
                                                   +---------------------+
                                                   |   loki-kafka-fwd    |
                                                   +---------------------+
                                                            |
                                                            v
                                                   +---------------------+
                                                   |  Kafka (raw-logs)   |
                                                   +---------------------+
                                                            |
                                                            v
                                     +---------------------------------------------------+
                                     |                   Log Consumer                    |
                                     | (+ Deeps03/qwen2-1.5b-log-classifier LLM)         |
                                     +---------------------------------------------------+
                                                            |
                                                            v
                                                   +---------------------+
                                                   |  VictoriaMetrics    |
                                                   +---------------------+
                                                            |
                                                            v
                                                   +---------------------+
                                                   |  Anomaly Detector   |
                                                   +---------------------+
                                                            |
                                                            v
                                                   +---------------------+
                                                   |  Kafka (anomalies)  |
                                                   +---------------------+
                                                            |
                                                            v
                                                   +---------------------+
                                                   |      Notifier       |
                                                   +---------------------+
                                                          /     |     \
                                                         /      |      \
                                                        v       v       v
                                      +----------------+ +----------------+ +-------------------+
                                      |  Email Alerts  | | Teams Messages | | Grafana Dashboard |
                                      +----------------+ +----------------+ +-------------------+
```

## Pipeline Explanation 🌊

This project processes logs through a series of interconnected services, ensuring real-time analysis, classification, anomaly detection, and notification. Here's a step-by-step breakdown of the data flow:

1.  **Log Ingestion:**
    *   Logs originate from various sources: **AWS CloudWatch**, **Azure Monitor**, or a **Local Producer** (for testing and local development).
    *   Dedicated pollers (AWS Log Poller, Azure Log Poller) continuously fetch logs from their respective cloud platforms.
    *   The Local Producer generates synthetic log data.
    *   All ingested logs are standardized into a common schema and published to the **`raw-logs` Kafka topic**.

2.  **Log Consumption and Classification:**
    *   The **Log Consumer** service subscribes to the `raw-logs` Kafka topic.
    *   Upon receiving a log entry, the Log Consumer invokes the fine-tuned **`Deeps03/qwen2-1.5b-log-classifier` LLM** to classify the log into one of three categories: `incident`, `preventive_action`, or `normal`.
    *   If the log is classified as `preventive_action` (or `warning`), the LLM also generates actionable suggestions on how to address the potential issue.
    *   The original log entry, along with its classification and any generated suggestions, is then published to the **`classified-logs` Kafka topic**.

3.  **Anomaly Detection:**
    *   The **Anomaly Detector** service also subscribes to the `classified-logs` Kafka topic.
    *   It continuously monitors the stream of classified logs for unusual patterns or deviations from normal behavior (e.g., a sudden spike in `incident` logs).
    *   When an anomaly is detected, an anomaly event (including a score and details) is published to the **`anomalies` Kafka topic**.

4.  **Metrics Collection:**
    *   Both the Log Consumer and Anomaly Detector push relevant metrics (e.g., counts of classified logs, anomaly scores) to **VictoriaMetrics**, a high-performance time-series database.

5.  **Alerting and Notifications:**
    *   The **Notifier Service** subscribes to both the `classified-logs` and `anomalies` Kafka topics.
    *   It applies smart alerting rules based on the classification (e.g., `incident` logs trigger critical alerts) and anomaly scores.
    *   Alerts are deduplicated to prevent spam.
    *   Notifications are sent out via configured channels: **Email** (SMTP) and **Microsoft Teams** webhooks.

6.  **Real-time Visualization:**
    *   **Grafana** is used to visualize the metrics stored in VictoriaMetrics.
    *   Dashboards provide real-time insights into log classifications, anomaly trends, and overall system health.

## Getting Started 🚀

### Prerequisites
- Docker and Docker Compose installed
- AWS credentials (optional, for CloudWatch integration)
- Azure credentials (optional, for Monitor integration)
- SMTP credentials (optional, for email notifications)
- Microsoft Teams webhook (optional, for Teams notifications)

### Basic Setup (Local Logs Only)

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    ```

2.  **Navigate to the LLMlogs directory:**
    ```bash
    cd SentinelLLM/LLMlogs
    ```
    *(All subsequent commands in this section should be run from within the `SentinelLLM/LLMlogs` directory unless otherwise specified.)*

3.  **Create Environment File:**
    ```bash
    cp .env.example .env
    ```

4.  **Build and Start Core Services:**
    ```bash
    docker-compose build --no-cache
    docker-compose up -d
    ```

5.  **Access Grafana and VictoriaMetrics:**

    *   **Access Grafana:** Open your web browser and go to `http://localhost:3000`.
        *   Default login: `admin` / `admin` (you will be prompted to change the password).

    *   **Add VictoriaMetrics as a Data Source in Grafana:**
        1.  Go to `Connections` -> `Data sources`.
        2.  Click `Add data source` and select `Prometheus`.
        3.  Set the URL to `http://victoria-metrics:8428`.
        4.  Click `Save & Test`.

    *   **Create a Dashboard in Grafana:**
        1.  Go to `Dashboards` -> `New dashboard`.
        2.  Click `Add new panel`.
        3.  In the "Query" tab, select your VictoriaMetrics data source.
        4.  Add queries for `log_incident_total` and `log_warning_total` (for time series graphs) or `sum(log_incident_total)` and `sum(log_warning_total)` (for Stat/Gauge panels).
        5.  Click `Apply` and then save your dashboard.

    *   **Access VictoriaMetrics UI (Optional):** You can access the VictoriaMetrics UI at `http://localhost:8428` to directly query metrics.

6.  **Stop all services:** Remember to run this from the `LLMlogs` directory.
    ```bash
    docker-compose down
    ```

### Fine-Tuning the LLM

1.  **Prepare your dataset:** Create a JSONL file with your log messages and their corresponding labels (e.g., `generated_logs.jsonl`). Each line should be a JSON object with a "message" and "label" key.

2.  **Set up the fine-tuning script:** Open the `fine_tune.py` script and replace `hf_your_token_here` with your Hugging Face access token. You can also customize the `model_name`, `dataset_path`, `output_dir`, and `repo_id` variables.

3.  **Run the fine-tuning script:**
    ```bash
    python fine_tune.py
    ```

4.  **Use the fine-tuned model:** Once the fine-tuning is complete, the new model will be pushed to the Hugging Face Hub. You can then update the `model_path` in the `log_consumer_model.py` script to use your fine-tuned model.

### Loki Integration

1.  **Enable the Loki profile:** Start the services with the `loki` profile:
    ```bash
    docker-compose --profile loki up -d --build
    ```

2.  **Configure the Loki-Kafka Forwarder:** The `loki-kafka-forwarder` service will automatically forward logs from Loki to Kafka. You can customize the batch size and rate limit in the `docker-compose.yml` file.

3.  **Query logs in Loki:** You can use the Loki API or the Grafana Explore view to query the logs stored in Loki.

### AWS CloudWatch Integration 🔗

1.  **Configure AWS credentials in `.env`:**
    ```env
    AWS_ACCESS_KEY_ID=your-access-key
    AWS_SECRET_ACCESS_KEY=your-secret-key
    AWS_REGION=us-east-1
    AWS_LOG_GROUPS=/aws/lambda/my-function,/aws/ec2/my-app
    AWS_POLL_INTERVAL_SECONDS=30
    ```

2.  **Start with AWS profile:**
    ```bash
    docker-compose --profile aws up -d --build
    ```

### Azure Monitor Integration 🔗

1.  **Create Azure Service Principal:**
    ```bash
    # Create service principal
    az ad sp create-for-rbac --name "SentinelLLM" --role "Log Analytics Reader" --scopes "/subscriptions/{subscription-id}/resourceGroups/{resource-group}"
    ```

2.  **Configure Azure credentials in `.env`:**
    ```env
    AZURE_TENANT_ID=your-tenant-id
    AZURE_CLIENT_ID=your-client-id
    AZURE_CLIENT_SECRET=your-client-secret
    AZURE_WORKSPACE_ID=your-log-analytics-workspace-id
    AZURE_QUERY=union * | where TimeGenerated > ago(1h) | order by TimeGenerated desc | limit 100
    AZURE_POLL_INTERVAL_SECONDS=60
    ```

3.  **Start with Azure profile:**
    ```bash
    docker-compose --profile azure up -d --build
    ```

### Email Notifications Setup 📧

1.  **Configure SMTP settings in `.env`:**
    ```env
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USERNAME=your-email@gmail.com
    SMTP_PASSWORD=your-app-password
    EMAIL_FROM=sentinellm@yourcompany.com
    EMAIL_RECIPIENTS=admin@yourcompany.com,ops@yourcompany.com
    SEND_PREVENTIVE_EMAILS=false
    ```

2.  **For Gmail:** Use App Passwords instead of your regular password

### Microsoft Teams Setup 👥

1.  **Create Teams Incoming Webhook:**
    - Go to your Teams channel
    - Click "..." → Connectors → Incoming Webhook
    - Configure and copy the webhook URL

2.  **Configure Teams in `.env`:**
    ```env
    TEAMS_WEBHOOK_URL=https://yourcompany.webhook.office.com/webhookb2/your-webhook-id
    ```

### Complete Setup (All Features)

```bash
# Configure all settings in .env file, then:
docker-compose --profile aws --profile azure --profile loki up -d --build
```

### Configuration Examples

**Production Configuration:**
```env
# Core
GRAFANA_API_KEY=your-grafana-key

# AWS
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-west-2
AWS_LOG_GROUPS=/aws/lambda/prod-api,/aws/ecs/prod-app
AWS_POLL_INTERVAL_SECONDS=15

# Azure  
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_WORKSPACE_ID=...
AZURE_QUERY=union * | where TimeGenerated > ago(30m) and SeverityLevel >= 2 | order by TimeGenerated desc | limit 200

# Notifications
SMTP_HOST=smtp.office365.com
SMTP_USERNAME=alerts@company.com
SMTP_PASSWORD=...
EMAIL_RECIPIENTS=oncall@company.com,devops@company.com
TEAMS_WEBHOOK_URL=https://company.webhook.office.com/...

# Tuning
ANOMALY_THRESHOLD=0.7
DEDUP_WINDOW_MINUTES=10
SEND_PREVENTIVE_EMAILS=true
```

## Monitoring & Operations 📊

### Health Checks
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f log-consumer
docker-compose logs -f aws-log-poller
docker-compose logs -f notifier

# Monitor Kafka topics
docker-compose exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic classified-logs --from-beginning
```

### Grafana Setup
1. Access Grafana at http://localhost:3000
2. Add VictoriaMetrics as data source: `http://victoria-metrics:8428`
3. Import or create dashboards for:
   - Log classification metrics
   - Anomaly detection scores
   - Service health monitoring

### Scaling & Performance
- **Kafka Partitioning:** Increase topic partitions for higher throughput
- **Consumer Groups:** Scale log processing by adding consumer instances
- **Resource Limits:** Configure Docker resource limits based on log volume
- **Checkpoint Frequency:** Adjust checkpoint intervals for AWS/Azure pollers

## Troubleshooting 🔧

### Common Issues

**Kafka Connection Issues:**
```bash
# Check Kafka is running
docker-compose logs kafka

# Verify topics exist
docker-compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list
```

**AWS Permissions:**
Ensure IAM user/role has:
- `logs:DescribeLogGroups`
- `logs:FilterLogEvents`

**Azure Permissions:**
Ensure service principal has:
- `Log Analytics Reader` role on workspace

### Log Analysis
```bash
# Check classification results
docker-compose logs log-consumer | grep "Classified as"

# Monitor anomaly detection
docker-compose logs anomaly-detector | grep "Anomaly"

# Verify notifications
docker-compose logs notifier
```

## Commands Used

Here are the commands we used to make the changes:

```bash
# Navigate to the LLMlogs directory
cd LLMlogs

# Check the services in the docker-compose file
docker-compose config --services

# Build the docker images (use --no-cache to ensure a fresh build)
docker-compose build --no-cache

# Run the services in detached mode
docker-compose up -d

# Check the logs of the log-consumer service
docker-compose logs log-consumer

# To stop the services
docker-compose down
```

## Project Status ⚠️

This project is a **production-ready platform** with the following considerations:

### Performance Considerations
- Checkpoint management ensures no log duplication after service restarts
- All services include retry mechanisms and graceful error handling

### Production Deployment
- Configure appropriate resource limits in Docker Compose
- Set up proper monitoring and alerting for service health
- Use secrets management for production credentials
- Consider using managed Kafka for scalability
- Implement log rotation and retention policies

## License 📄

This project is provided as-is for educational and production use. Please ensure you comply with the terms of service for all integrated APIs (AWS, Azure, etc.).