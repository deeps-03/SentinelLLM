# SentinelLLM 🚀

## Project Description 📝
This project provides a complete, production-ready **real-time log analysis and streaming platform** that leverages a robust stack of Dockerized services. It features AI-powered log classification using the **Google Gemini API**, cloud log ingestion from **AWS CloudWatch** and **Azure Monitor**, and comprehensive alerting via **Email** and **Microsoft Teams**.

## Key Features ✨

### Core Features
*   **AI-Powered Log Classification:** Uses the **Google Gemini API** (`gemini-1.5-flash`) to intelligently classify logs into `incident` 🚨, `preventive_action` 🛠️, or `normal`.
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
*   **AI Model:** Google Gemini API (`gemini-1.5-flash`)
*   **Python Libraries:** 
    *   `google-generativeai` - AI classification
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
                   │+ Gemini AI │                                   │
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

## How the LLM is Used

The core intelligence of this project comes from the integration with the Gemini API in the `log_consumer_model.py` script.

1.  **Model:** We use the `gemini-1.5-flash` model, which provides a great balance of speed and reasoning capabilities for this classification task.

2.  **Prompting:** For each log message consumed from Kafka, the service sends a specifically crafted prompt to the Gemini API. The prompt instructs the model to act as an analysis engine and classify the log into one of three categories:
    *   `incident`: For critical errors or failures requiring immediate attention.
    *   `preventive_action`: For warnings or potential future issues that should be investigated.
    *   `normal`: For routine, informational messages.

3.  **Rate Limiting:** To handle the API's free tier quota (15 requests per minute), the consumer script has a hardcoded `time.sleep(5)` delay in its main loop. This ensures we stay within the per-minute limit.

4.  **Output Processing:** Classified logs are published to the `classified-logs` Kafka topic for consumption by the notifier service.

## Data Flow & Topics

### Kafka Topics
- **`raw-logs`**: Structured logs from AWS CloudWatch, Azure Monitor, and local producers
- **`classified-logs`**: Logs after AI classification by Gemini
- **`anomalies`**: Anomaly detection results with scores and details

### Schema Examples

**Raw Log Entry:**
```json
{
  "source": "aws-cloudwatch|azure-monitor|local",
  "host": "server-name-or-resource-id",
  "timestamp": 1640995200000,
  "level": "ERROR|WARNING|INFO|DEBUG",
  "message": "Actual log message content",
  "service": "service-name",
  "log_group": "log-group-name",
  "raw_data": {...}
}
```

**Classified Log Entry:**
```json
{
  ...raw_log_fields,
  "classification": "incident|preventive_action|normal",
  "classified_timestamp": 1640995200000,
  "source_topic": "raw-logs"
}
```

**Anomaly Entry:**
```json
{
  "type": "log_volume_anomaly",
  "score": 2.5,
  "details": "High Incident Anomaly: Current incidents (25) > 2x historical average (10.5)",
  "timestamp": 1640995200000,
  "source": "anomaly-detector"
}
```

## Getting Started 🚀

### Prerequisites
- Docker and Docker Compose installed
- Google AI API key (required)
- AWS credentials (optional, for CloudWatch integration)
- Azure credentials (optional, for Monitor integration)
- SMTP credentials (optional, for email notifications)
- Microsoft Teams webhook (optional, for Teams notifications)

### Basic Setup (Local Logs Only)

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd SentinelLLM/LLMlogs
    ```

2.  **Create Environment File:**
    ```bash
    cp .env.example .env
    ```

3.  **Configure Required Settings:**
    Edit the `.env` file and set at minimum:
    ```env
    GEMINI_API_KEY=your-google-ai-api-key-here
    ```

4.  **Start Core Services:**
    ```bash
    docker-compose up -d --build
    ```

5.  **Access Services:**
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
GEMINI_API_KEY=your-api-key
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
AZURE_QUERY=AppTraces | where TimeGenerated > ago(30m) and SeverityLevel >= 2 | order by TimeGenerated desc | limit 200

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

**API Rate Limits:**
- Gemini API: 15 requests/minute (free tier)
- Adjust sleep intervals if needed

### Log Analysis
```bash
# Check classification results
docker-compose logs log-consumer | grep "Classified as"

# Monitor anomaly detection
docker-compose logs anomaly-detector | grep "Anomaly"

# Verify notifications
docker-compose logs notifier
```

## Project Status & API Limits ⚠️

This project is a **production-ready platform** with the following considerations:

### API Limitations
- **Google Gemini API (Free Tier):** 15 requests per minute, 50 per day
- **AWS CloudWatch:** Standard AWS API rate limits apply
- **Azure Monitor:** Standard Azure API rate limits apply

### Performance Considerations
- The log consumer includes rate limiting to respect Gemini API quotas
- For high-volume environments, consider upgrading to Gemini API paid tiers
- Checkpoint management ensures no log duplication after service restarts
- All services include retry mechanisms and graceful error handling

### Production Deployment
- Configure appropriate resource limits in Docker Compose
- Set up proper monitoring and alerting for service health
- Use secrets management for production credentials
- Consider using managed Kafka for scalability
- Implement log rotation and retention policies

## License 📄

This project is provided as-is for educational and production use. Please ensure you comply with the terms of service for all integrated APIs (Google Gemini, AWS, Azure, etc.).