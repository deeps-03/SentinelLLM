# SentinelLLM 🚀

## Project Description 📝
This project provides a complete, production-ready **real-time log analysis and streaming platform** that leverages a robust stack of Dockerized services. It features AI-powered log classification using a local LLM, cloud log ingestion from **AWS CloudWatch** and **Azure Monitor**, and comprehensive alerting via **Email** and **Microsoft Teams**.

## Key Features ✨

### Core Features
*   **AI-Powered Log Classification:** Uses a local `Qwen/Qwen2-1.5B-Instruct` model to intelligently classify logs into `incident` 🚨, `preventive_action` 🛠️, or `normal`.
*   **Real-time Streaming:** Kafka-based log streaming architecture for high-throughput processing.
*   **Anomaly Detection:** Automatic detection of unusual log patterns with configurable thresholds.
*   **Metrics Collection:** Classified log counts and anomalies pushed to VictoriaMetrics for time-series storage.
*   **Real-time Visualization:** Grafana dashboards for live insights into log classification metrics.

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
*   **AI Model:** Qwen/Qwen2-1.5B-Instruct (via LlamaCpp)
*   **Python Libraries:** 
    *   `langchain`, `langchain-community`, `llama-cpp-python` - AI classification
    *   `kafka-python` - Streaming
    *   `boto3` - AWS integration
    *   `azure-monitor-query`, `azure-identity` - Azure integration
    *   `requests` - HTTP communications
    *   `python-dotenv` - Configuration management
*   **Infrastructure:** Kafka & Zookeeper, VictoriaMetrics, Grafana
*   **Cloud Platforms:** AWS CloudWatch, Azure Monitor/Log Analytics
*   **Notification Systems:** SMTP Email, Microsoft Teams Webhooks
*   **Containerization:** Docker & Docker Compose

## Architecture Diagram 🗺️
```
                    Cloud Log Sources                           Notification Channels
                         │                                           │
        ┌────────────────┼────────────────┐                         │
        │                │                │                         │
   ┌────▼───┐       ┌────▼────┐      ┌────▼────┐                   │
   │AWS     │       │Azure    │      │Local    │                   │
   │Logs    │       │Monitor  │      │Producer │                   │
   │Poller  │       │Poller   │      │         │                   │
   └────┬───┘       └────┬────┘      └────┬────┘                   │
        │                │                │                        │
        └────────────────┼────────────────┘                        │
                         │                                          │
                    ┌────▼────┐                                     │
                    │ Kafka   │                                     │
                    │raw-logs │                                     │
                    └────┬────┘                                     │
                         │                                          │
                   ┌─────▼──────┐                                   │
                   │Log Consumer│                                   │
                   │+ XGBoost   │                                   │
                   │+ Qwen LLM  │                                   │
                   └─────┬──────┘                                   │
                         │                                          │
              ┌──────────┼───────────┐                             │
              │          │           │                             │
         ┌────▼───┐ ┌────▼───────┐  │                             │
         │Kafka   │ │Victoria    │  │                             │
         │class.  │ │Metrics     │  │                             │
         │logs    │ │            │  │                             │
         └────┬───┘ └────┬───────┘  │                             │
              │          │          │                             │
              │     ┌────▼────┐     │                             │
              │     │Anomaly  │     │                             │
              │     │Detector │     │                             │
              │     └────┬────┘     │                             │
              │          │          │                             │
              │      ┌───▼────┐     │                             │
              │      │Kafka   │     │                             │
              │      │anomal. │     │                             │
              │      └───┬────┘     │                             │
              │          │          │                             │
              └──────────┼──────────┘                             │
                         │                                         │
                   ┌─────▼──────┐                                  │
                   │ Notifier   │──────────────────────────────────┘
                   │ Service    │
                   └────────────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼───┐ ┌────▼────┐┌───▼────┐
         │Email   │ │Teams    ││Grafana │
         │Alerts  │ │Messages ││Dashbrd │
         └────────┘ └─────────┘└────────┘
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
    *   Upon receiving a log entry, the Log Consumer first uses a pre-trained **XGBoost model** (along with a TF-IDF vectorizer and Label Encoder) to classify the log into one of three categories: `incident`, `preventive_action`, or `normal`.
    *   If the log is classified as `preventive_action` (or `warning`), the Log Consumer then invokes the **Qwen/Qwen2-1.5B-Instruct LLM**.
    *   The LLM analyzes the log message and generates actionable suggestions on how to address the potential issue.
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

4.  **Train the ML Models (XGBoost, TF-IDF Vectorizer, Label Encoder):**
    These models are used for the initial classification of log messages into `incident`, `preventive_action`, or `normal`.

    a. **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

    b. **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

    c. **Run the training script:**
    ```bash
    python model_train.py
    ```
    This script will generate `xgboost_model.pkl`, `vectorizer.pkl`, and `label_encoder.pkl` in the current directory.

    d. **Deactivate the virtual environment:**
    ```bash
    deactivate
    ```

5.  **Build and Start Core Services:**
    ```bash
    docker-compose build --no-cache
    docker-compose up -d
    ```

6.  **Access Services:**
    - Grafana: http://localhost:3000 (admin/admin)
    - VictoriaMetrics: http://localhost:8428

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
docker-compose --profile aws --profile azure up -d --build
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