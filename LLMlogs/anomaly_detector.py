import os
import time
import requests
import json

# Load environment variables
from dotenv import load_dotenv
# Load environment variables from a .env file in the same directory.
# This is used to securely store the Grafana API key.
load_dotenv()

GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY")
if not GRAFANA_API_KEY:
    print("Error: GRAFANA_API_KEY not found in .env file.")
    exit(1)

# Configuration
PROMETHEUS_URL = "http://victoria-metrics:8428/api/v1/query"
GRAFANA_URL = "http://grafana:3000"
ALERT_API_ENDPOINT = f"{GRAFANA_URL}/api/annotations"

# Anomaly detection thresholds
INCIDENT_THRESHOLD_MULTIPLIER = 2
WARNING_THRESHOLD_MULTIPLIER = 2

# Time ranges for metric queries
CURRENT_METRIC_RANGE = "5m"  # Last 5 minutes for current metrics
HISTORICAL_METRIC_RANGE = "6h" # Last 6 hours for historical average

# Fetches time-series data for a given metric from VictoriaMetrics.
def fetch_metric(metric_name, time_range):
    query = f"{metric_name}[{time_range}]"
    params = {"query": query}
    try:
        response = requests.get(PROMETHEUS_URL, params=params)
        response.raise_for_status()
        result = response.json()
        if result["status"] == "success" and result["data"]["result"]:
            # For range queries, we expect a list of [timestamp, value] pairs
            # We'll take the last value for simplicity for current metrics,
            # and average for historical.
            return result["data"]["result"]
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching metric {metric_name}: {e}")
        return []

def calculate_average(metric_data):
    if not metric_data:
        return 0
    # metric_data is a list of series, each series has a list of [timestamp, value]
    # We need to flatten this and get all values
    all_values = []
    for series in metric_data:
        for value_pair in series["values"]:
            all_values.append(float(value_pair[1]))
    if not all_values:
        return 0
    return sum(all_values) / len(all_values)

# Sends an annotation to Grafana to mark an anomaly on dashboards.
def send_grafana_alert(message):
    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": message,
        "tags": ["anomaly", "auto-generated"],
        "isRegion": False,
        "time": int(time.time() * 1000) # Current time in milliseconds
    }
    try:
        response = requests.post(ALERT_API_ENDPOINT, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        print(f"Grafana alert sent: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Grafana alert: {e}")

def main():
    print("Starting Anomaly Detector...")
    # This is the main loop that runs continuously to check for anomalies.
    while True:
        print(f"[{time.ctime()}] Checking for anomalies...")

        # Fetch current metrics (last 5 minutes)
        current_incidents_data = fetch_metric("log_incident_total", CURRENT_METRIC_RANGE)
        current_warnings_data = fetch_metric("log_warning_total", CURRENT_METRIC_RANGE)

        # Prometheus range query returns a list of series, each with 'values'
        # We need to get the last value for the 'current' count
        current_incidents = 0
        if current_incidents_data:
            for series in current_incidents_data:
                if series["values"]:
                    current_incidents += float(series["values"][-1][1]) # Sum up last values from all series

        current_warnings = 0
        if current_warnings_data:
            for series in current_warnings_data:
                if series["values"]:
                    current_warnings += float(series["values"][-1][1]) # Sum up last values from all series

        # Fetch historical metrics (last 6 hours)
        historical_incidents_data = fetch_metric("log_incident_total", HISTORICAL_METRIC_RANGE)
        historical_warnings_data = fetch_metric("log_warning_total", HISTORICAL_METRIC_RANGE)

        historical_incidents_avg = calculate_average(historical_incidents_data)
        historical_warnings_avg = calculate_average(historical_warnings_data)

        print(f"  Current Incidents: {current_incidents}, Historical Avg Incidents: {historical_incidents_avg:.2f}")
        print(f"  Current Warnings: {current_warnings}, Historical Avg Warnings: {historical_warnings_avg:.2f}")

        anomaly_detected = False
        alert_message = []

        if historical_incidents_avg > 0 and current_incidents > INCIDENT_THRESHOLD_MULTIPLIER * historical_incidents_avg:
            anomaly_detected = True
            alert_message.append(f"High Incident Anomaly: Current incidents ({current_incidents}) > {INCIDENT_THRESHOLD_MULTIPLIER}x historical average ({historical_incidents_avg:.2f})")

        if historical_warnings_avg > 0 and current_warnings > WARNING_THRESHOLD_MULTIPLIER * historical_warnings_avg:
            anomaly_detected = True
            alert_message.append(f"High Warning Anomaly: Current warnings ({current_warnings}) > {WARNING_THRESHOLD_MULTIPLIER}x historical average ({historical_warnings_avg:.2f})")

        if anomaly_detected:
            full_message = "Anomaly Detected! " + " | ".join(alert_message)
            print(f"!!! {full_message} !!!")
            send_grafana_alert(full_message)
        else:
            print("  No anomalies detected.")

        time.sleep(60) # Check every 60 seconds

if __name__ == "__main__":
    main()
