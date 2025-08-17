# SentinelLLM 🚀

## Project Description 📝
This project provides a complete, local end-to-end prototype for **real-time log analysis and streaming**. It leverages a robust stack of Dockerized services, with log classification powered by the **Google Gemini API** to intelligently categorize log data in real-time.

## Key Features ✨
*   **Log Generation:** A Python script generates synthetic log data (INFO, WARNING, ERROR, etc.) and streams it to a Kafka topic.
*   **AI-Powered Log Classification:** A log consumer service uses the **Google Gemini API** (`gemini-1.5-flash`) to classify logs into `incident` 🚨, `preventive_action` 🛠️, or `normal`.
*   **Metrics Collection:** Classified log counts are pushed as metrics to VictoriaMetrics for high-performance time-series storage.
*   **Real-time Visualization:** Includes a Grafana service ready to be configured for live insights into log classification metrics.
*   **Containerized Environment:** All services (Kafka, Zookeeper, VictoriaMetrics, Grafana, and the Python apps) run seamlessly within Docker Compose for easy setup and portability.
*   **Anomaly Detection:** A service that automatically detects unusual log patterns and can trigger alerts in Grafana.

## Technologies Used 🛠️
*   **AI Model:** Google Gemini API (`gemini-1.5-flash`)
*   **Python Libraries:** `google-generativeai`, `kafka-python`, `requests`, `python-dotenv`
*   **Kafka & Zookeeper:** For distributed log streaming.
*   **VictoriaMetrics:** For high-performance metrics storage.
*   **Grafana:** For monitoring, visualization, and alerting.
*   **Docker & Docker Compose:** For containerization and orchestration.

## Architecture Diagram 🗺️
```
+-----------------+      +----------------+      +-------------------------+      +-------------------+      +-----------------+
|  Log Producer   |----->|     Kafka      |----->|   Log Consumer          |----->|  VictoriaMetrics  |----->|     Grafana     |
| (Generates Logs)|      | (Log Streaming)|      | (Calls Gemini API)      |      |  (Stores Metrics) |      | (Visualizes Data)|
+-----------------+      +----------------+      +-------------------------+      +---------+---------+      +--------+--------+
                                                                                             |                         ^
                                                                                             | (Reads Metrics)         | (Sends Alerts)
                                                                                             |                         |
                                                                                   +---------▼---------+---------------+
                                                                                   | Anomaly Detector  |
                                                                                   |(Detects Anomalies)|
                                                                                   +-------------------+
```

## How the LLM is Used

The core intelligence of this project comes from the integration with the Gemini API in the `log_consumer_model.py` script.

1.  **Model:** We use the `gemini-1.5-flash` model, which provides a great balance of speed and reasoning capabilities for this classification task.

2.  **Prompting:** For each log message consumed from Kafka, the service sends a specifically crafted prompt to the Gemini API. The prompt instructs the model to act as an analysis engine and classify the log into one of three categories:
    *   `incident`: For critical errors or failures.
    *   `preventive_action`: For warnings or potential future issues.
    *   `normal`: For routine, informational messages.

3.  **Rate Limiting:** To handle the API's free tier quota (15 requests per minute), the consumer script has a hardcoded `time.sleep(5)` delay in its main loop. This ensures we stay within the per-minute limit, though the separate daily limit may still be reached with extended use.

## Getting Started 🚀

Follow these steps to get the SentinelLLM project up and running locally.

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd SentinelLLM
    ```

2.  **Create Environment File:**
    Navigate into the `LLMlogs` directory. Create the `.env` file.
    ```bash
    cd LLMlogs
    touch .env
    ```

3.  **Add API Keys:**
    Open the `.env` file and add your Google AI API Key. If you plan to use the anomaly detector's alerting feature, you can also add your Grafana API key.
    ```
    GEMINI_API_KEY='Your-Google-AI-API-Key-Here'
    # Optional: For anomaly detector alerts
    GRAFANA_API_KEY='Your-Generated-Grafana-API-Key-Here'
    ```

4.  **Build and Run Services:**
    From the `LLMlogs` directory, run Docker Compose. This will build the images and start all services in the background.
    ```bash
    docker-compose up -d --build
    ```

5.  **Check the Logs:**
    You can watch the AI classification in real-time by viewing the logs of the `log-consumer` service.
    ```bash
    docker-compose logs -f log-consumer
    ```

6.  **Access Grafana:**
    *   Open your web browser and go to `http://localhost:3000`.
    *   Default login: `admin` / `admin`.
    *   Set up VictoriaMetrics as a Prometheus data source at `http://victoria-metrics:8428`.

7.  **Stop all services:**
    When you are finished, stop all services from the `LLMlogs` directory.
    ```bash
    docker-compose down
    ```

## Project Status & API Limits

This project is a functional proof-of-concept. It currently uses the free tier of the Google Gemini API, which has strict rate limits (e.g., 15 requests per minute and 50 per day). The `log-consumer` has a built-in delay to respect the per-minute limit, but the per-day limit will still be reached with continuous use.