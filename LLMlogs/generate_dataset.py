import json
import random
import argparse
import time
import numpy as np
import re

# --- Consolidated Placeholder Values ---
PLACEHOLDERS = {
    "user": ["admin", "guest", "dev", "system", "root", "monitor"],
    "config_file": ["app.conf", "nginx.conf", "log4j.properties"],
    "instance_id": lambda: f"i-{random.randint(10000, 99999)}",
    "file_path": ['/var/log/app.log', '/home/user/data.csv', '/etc/config.json', "/etc/config.conf", "/var/log/syslog", "/app/data.json"],
    "bucket": ["my-bucket", "data-lake", "backup-storage"],
    "func_name": ["lambdaHandler", "process_event", "init_module", "process_request", "calculate_metrics", "log_event", "send_heartbeat"],
    "db_name": ["maindb", "analytics", "usersdb", "inventory"],
    "stack_name": ["stack-prod", "stack-dev", "stack-staging"],
    "table": ["users", "orders", "metrics", "products", "logs"],
    "vm_id": lambda: f"vm-{random.randint(100, 999)}",
    "container": ["container-prod-1", "container-dev-2", "container-web"],
    "service": ["auth-service", "payment-service", "orderservice", "notification_service", "logging_service", "monitoring-agent"],
    "hub": ["event-hub-prod", "event-hub-dev"],
    "drive": ["/dev/sda1", "/mnt/data", "/var/log", "/opt/app"],
    "server": ["web-01", "app-02", "db-01", "cache-03", "worker-5"],
    "func": ["legacy_method", "deprecatedFunc", "old_api", "unoptimized_query"],
    "api_endpoint": ["/api/v1/users", "/api/v1/orders", "/api/v1/products", "/api/v2/auth"],
    "metric": ["CPUUtilization", "MemoryUsage", "DiskIO", "NetworkIn"],
    "account": ["storage-prod", "storage-dev", "storage-archive"],
    "pod": lambda: f"pod-{random.randint(10, 999)}",
    "reason": ["timeout", "connection refused", "access denied", "invalid credentials", "connection reset", "resource exhausted"],
    "value": lambda: random.randint(0, 1000),
    "time_ms": lambda: random.randint(1, 200),
    "db_error_code": lambda: random.randint(1000, 9999),
    "module": ["auth_service", "data_processor", "api_gateway", "report_generator", "user_management"],
    "line": lambda: random.randint(50, 1500),
    "pid": lambda: random.randint(100, 99999),
    "host": ["external-api.com", "internal-db.local", "message-queue.internal", "third-party.service.com"],
    "param_name": ["userId", "transactionId", "sessionId", "query"],
    "task_id": lambda: f"task-{random.randint(100, 9999)}",
    "partition": lambda: random.randint(1, 16),
    "queue": ["high-priority-queue", "default-queue", "low-priority-queue"],
    "var_name": ["temp_var", "unused_param", "loop_counter"],
    "domain": ["example.com", "internal.net", "api.example.org"],
    "vnet": ["vnet-prod", "vnet-dev"],
    "vault": ["prod-key-vault", "dev-key-vault"],
    "ip_address": lambda: f"{random.randint(10, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}",
}

# --- Consolidated Log Templates ---

NORMAL_TEMPLATES = [
    "INFO: User {user} logged in successfully from IP {ip_address}.",
    "INFO: Data processed for report generation for user {user}.",
    "INFO: System health check passed successfully.",
    "INFO: New session started for user {user}.",
    "INFO: Application started successfully on server {server}.",
    "INFO: Configuration loaded from {config_file}.",
    "INFO: Received request from IP {ip_address} for endpoint {api_endpoint}.",
    "DEBUG: Variable '{var_name}' value: {value}.",
    "DEBUG: Entering function '{func_name}'.",
    "DEBUG: Function {func_name} completed in {time_ms}ms.",
    "AWS EC2 instance {instance_id} started successfully.",
    "AWS S3 object {file_path} uploaded to bucket {bucket}.",
    "AWS Lambda function {func_name} executed successfully.",
    "AWS RDS instance {db_name} backup completed.",
    "AWS CloudFormation stack {stack_name} deployed successfully.",
    "AWS DynamoDB table {table} created.",
    "AWS ECS task {task_id} is now running.",
    "AWS EKS pod {pod} has been scheduled on node {server}.",
    "AWS CloudTrail event logged for user {user}.",
    "AWS CloudWatch metric {metric} published.",
    "Azure VM {vm_id} provisioned successfully.",
    "Azure Blob Storage file {file_path} uploaded to container {container}.",
    "Azure SQL Database {db_name} backup completed.",
    "Azure App Service {service} deployed successfully.",
    "Azure Function {func_name} executed successfully.",
    "Azure Key Vault secret accessed by {user}.",
    "Azure Event Hub {hub} received message batch.",
    "Azure Kubernetes Service pod {pod} is now running.",
    "Azure Monitor metrics sent for {vm_id}.",
    "Azure Load Balancer probe succeeded for {server}.",
]

WARNING_TEMPLATES = [
    "WARNING: Low disk space on {drive} on server {server}.",
    "WARNING: High CPU usage detected on {server}.",
    "WARNING: Deprecated function {func} called in module {module}.",
    "WARNING: Failed to refresh cache. Using stale data.",
    "WARNING: Too many open files detected. Current count: {value}.",
    "WARNING: High latency ({time_ms}ms) detected for API {api_endpoint}.",
    "WARNING: Unused variable '{var_name}' in function {func_name}.",
    "WARNING: Potential SQL injection attempt from IP {ip_address}.",
    "WARNING: Certificate for {domain} will expire in {value} days.",
    "AWS CloudWatch alarm triggered: {metric} usage above threshold.",
    "AWS EC2 instance {instance_id} approaching memory limit.",
    "AWS S3 bucket {bucket} nearing object limit.",
    "AWS RDS instance {db_name} high latency warning.",
    "AWS API Gateway rate limit approaching for {api_endpoint}.",
    "AWS Lambda function {func_name} hitting timeout threshold.",
    "AWS ECS service {service} scaling delayed.",
    "AWS ELB health check failing for target {host}.",
    "AWS DynamoDB table {table} read capacity almost consumed.",
    "AWS CloudTrail log delivery delayed to S3 bucket {bucket}.",
    "Azure Monitor detected high CPU usage on VM {vm_id}.",
    "Azure Storage account {account} throttling requests.",
    "Azure App Service {service} response time is high.",
    "Azure SQL Database {db_name} is reaching its DTU limit.",
    "Azure Kubernetes Service pod {pod} is restarting frequently.",
    "Azure Event Hub {hub} is nearing its throughput units.",
    "Azure Load Balancer probe failed for backend {server}.",
    "Azure Virtual Network {vnet} is experiencing packet loss.",
    "Azure Service Bus queue {queue} length is increasing.",
    "Azure Key Vault {vault} certificate is expiring soon.",
]

ERROR_TEMPLATES = [
    "ERROR: Database connection failed: {reason}. DB Error Code: {db_error_code}.",
    "ERROR: NullPointerException in {module} at line {line}.",
    "ERROR: Disk full on {drive}. Cannot write to {file_path}.",
    "ERROR: Authentication failed for user {user} from IP {ip_address}.",
    "ERROR: Service {service} is unreachable. Request to {host} timed out.",
    "ERROR: Out of memory error in process {pid} on server {server}.",
    "ERROR: File not found: {file_path}.",
    "ERROR: Network timeout connecting to {host}.",
    "ERROR: Invalid input parameter: {param_name}. Value: '{value}'.",
    "AWS EC2 instance {instance_id} failed to start due to {reason}.",
    "AWS S3 bucket {bucket} access denied for user {user}.",
    "AWS Lambda function {func_name} failed with error code {db_error_code}: {reason}.",
    "AWS RDS connection error: {reason}.",
    "AWS API Gateway returned 500 Internal Server Error for {api_endpoint}.",
    "AWS CloudFormation stack {stack_name} failed to deploy.",
    "AWS DynamoDB request throttled for table {table}.",
    "AWS ECS task {task_id} failed to start container {service}.",
    "AWS EKS pod {pod} crashed with exit code {value}.",
    "AWS CloudWatch Agent disconnected from {host}.",
    "Azure VM {vm_id} failed to allocate resources.",
    "Azure Blob Storage container {container} access denied.",
    "Azure SQL Database {db_name} connection failed.",
    "Azure App Service {service} crashed unexpectedly.",
    "Azure Function {func_name} execution timed out.",
    "Azure Key Vault access denied for {user}.",
    "Azure Event Hub {hub} partition {partition} failed with error {db_error_code}.",
    "Azure Service Bus queue {queue} dead-lettered a message.",
    "Azure Kubernetes pod {pod} terminated unexpectedly.",
    "Azure Monitor agent stopped sending logs from {host}.",
]

def fill_template(template):
    """Fills a log template with placeholder values."""
    # Use regex to find all placeholders in the form of {placeholder_name}
    placeholders_in_template = re.findall(r'\{(\w+)\}', template)
    
    format_args = {}
    for p_name in placeholders_in_template:
        value_source = PLACEHOLDERS.get(p_name)
        if value_source:
            if callable(value_source):
                format_args[p_name] = value_source()
            else:
                format_args[p_name] = random.choice(value_source)
        else:
            # Fallback for unknown placeholders
            format_args[p_name] = "UNKNOWN"
            
    return template.format(**format_args)

def generate_log_entry(label):
    """Generates a single log entry with a given label."""
    if label == "incident":
        template = random.choice(ERROR_TEMPLATES)
        level = "ERROR"
    elif label == "preventive_action":
        template = random.choice(WARNING_TEMPLATES)
        level = "WARNING"
    else: # normal
        template = random.choice(NORMAL_TEMPLATES)
        level = random.choice(["INFO", "DEBUG"])

    message = fill_template(template)
    
    log_entry = {
        "timestamp": time.time(),
        "level": level,
        "message": message,
        "service": random.choice(PLACEHOLDERS["service"]),
        "label": label
    }
    return log_entry

def main():
    parser = argparse.ArgumentParser(description="Generate a synthetic log dataset.")
    parser.add_argument("num_logs", type=int, help="The number of log entries to generate.")
    parser.add_argument("--output_file", type=str, default="generated_logs.jsonl", help="The name of the output file.")
    args = parser.parse_args()

    num_logs = args.num_logs
    output_file = args.output_file

    print(f"Generating {num_logs} log entries and saving to {output_file}...")

    # Define the distribution of log types
    # 40% normal, 40% preventive_action, 20% incident
    labels = ["normal"] * int(num_logs * 0.4) + \
             ["preventive_action"] * int(num_logs * 0.4) + \
             ["incident"] * int(num_logs * 0.2)
    
    # Ensure the list has the exact number of logs requested
    while len(labels) < num_logs:
        labels.append("normal")
    
    random.shuffle(labels)

    with open(output_file, "w") as f:
        for i in range(num_logs):
            label = labels[i]
            log = generate_log_entry(label)
            f.write(json.dumps(log) + "\n")
            if (i + 1) % 1000 == 0:
                print(f"  ... {i + 1}/{num_logs} logs generated")

    print("Dataset generation complete.")
    print(f"Generated {num_logs} logs in '{output_file}'.")

if __name__ == "__main__":
    main()