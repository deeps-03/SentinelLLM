import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
import pickle

# This function generates a synthetic dataset of log messages with predefined labels.
def generate_synthetic_logs(num_samples=1000):
    logs = []
    labels = []

    # --------------------------- ERROR LOGS ---------------------------
    error_templates = [
        # Existing ones
        "failed to connect to database: {reason}",
        "NullPointerException in {module} at line {line}",
        "Disk full on {drive}",
        "Authentication failed for user {user}",
        "Service {service} is unreachable",
        "Database connection failed: {db_error_code}",
        "Out of memory error in process {pid}",
        "File not found: {file_path}",
        "Network timeout connecting to {host}",
        "Invalid input parameter: {param_name}",
        "High CPU usage detected....",
        "NullPointerException in main service....",
        "Database connection failed....",
        "Authentication failed for user 'admin'....",
        "Service 'payment' is unreachable....",

        # AWS-style errors
        "AWS EC2 instance {instance_id} failed to start due to {reason}",
        "AWS S3 bucket {bucket} access denied for user {user}",
        "AWS Lambda function {func_name} failed with error code {db_error_code}",
        "AWS RDS connection error: {reason}",
        "AWS API Gateway returned 500 Internal Server Error for {api_endpoint}",
        "AWS CloudFormation stack {stack_name} failed to deploy", 
        "AWS DynamoDB request throttled for table {table}",
        "AWS ECS task {task_id} failed to start container {service}",
        "AWS EKS pod {pod} crashed with exit code {pid}",
        "AWS CloudWatch Agent disconnected from {host}",

        # Azure-style errors
        "Azure VM {vm_id} failed to allocate resources", 
        "Azure Blob Storage container {container} access denied", 
        "Azure SQL Database {db_name} connection failed", 
        "Azure App Service {service} crashed unexpectedly", 
        "Azure Function {func_name} execution timed out", 
        "Azure Key Vault access denied for {user}",
        "Azure Event Hub {hub} partition {partition} failed with error {db_error_code}",
        "Azure Service Bus queue {queue} dead-lettered message", 
        "Azure Kubernetes pod {pod} terminated unexpectedly", 
        "Azure Monitor agent stopped sending logs from {host}",
    ]

    # --------------------------- WARNING LOGS ---------------------------
    warning_templates = [
        # Existing ones
        "WARNING: Low disk space on {drive}",
        "WARNING: High CPU usage detected on {server}",
        "WARNING: Deprecated function {func} called",
        "WARNING: Cache refresh failed, using old data",
        "WARNING: Too many open files",
        "WARNING: High latency detected for API {api_endpoint}",
        "WARNING: Unused variable {var_name} in function {func_name}",
        "WARNING: Potential SQL injection attempt from IP {ip_address}",
        "WARNING: Certificate will expire soon for {domain}",
        "WARNING: Failed to refresh cache. Using stale data.",
        "Deprecated API endpoint accessed....",
        "Disk space low on /var/log....",
        "Failed to refresh cache....",

        # AWS-style warnings
        "AWS CloudWatch alarm triggered: {metric} usage above threshold", 
        "AWS EC2 instance {instance_id} approaching memory limit", 
        "AWS S3 bucket {bucket} nearing object limit", 
        "AWS RDS instance {db_name} high latency warning", 
        "AWS API Gateway rate limit approaching for {api_endpoint}", 
        "AWS Lambda function {func_name} hitting timeout threshold", 
        "AWS ECS service {service} scaling delayed", 
        "AWS ELB health check failing for target {host}",
        "AWS DynamoDB table {table} read capacity almost consumed", 
        "AWS CloudTrail log delivery delayed to S3 bucket {bucket}",

        # Azure-style warnings
        "Azure Monitor detected high CPU usage on VM {vm_id}", 
        "Azure Storage account {account} throttling requests", 
        "Azure App Service {service} response time high", 
        "Azure SQL Database {db_name} reaching DTU limit", 
        "Azure Kubernetes Service pod {pod} restarting frequently", 
        "Azure Event Hub {hub} nearing throughput units", 
        "Azure Load Balancer probe failed for backend {server}",
        "Azure Virtual Network {vnet} experiencing packet loss", 
        "Azure Service Bus queue {queue} length increasing", 
        "Azure Key Vault {vault} certificate expiring soon", 
    ]

    # --------------------------- NORMAL / INFO LOGS ---------------------------
    normal_templates = [
        # Existing ones
        "INFO: User {user} logged in successfully.",
        "INFO: Data processed for report generation.",
        "INFO: System health check passed.",
        "INFO: New session started for user {user}.",
        "DEBUG: Variable 'x' value: {value}.",
        "DEBUG: Entering function 'process_data'.",
        "INFO: Application started successfully.",
        "INFO: Configuration loaded from {config_file}.",
        "INFO: Received request from IP {ip_address}.",
        "DEBUG: Function {func_name} completed in {time_ms}ms.",
        "New session started....",
        "User logged in successfully....",
        "Data processed for report generation....",
        "System health check passed....",
        "Entering function 'process_data'....",
        "Variable 'x' value: 10....",

        # AWS-style info logs
        "AWS EC2 instance {instance_id} started successfully", 
        "AWS S3 object {file_path} uploaded to bucket {bucket}", 
        "AWS Lambda function {func_name} executed successfully", 
        "AWS RDS instance {db_name} backup completed", 
        "AWS CloudFormation stack {stack_name} deployed", 
        "AWS DynamoDB table {table} created", 
        "AWS ECS task {task_id} running", 
        "AWS EKS pod {pod} scheduled on node {server}", 
        "AWS CloudTrail event logged for user {user}", 
        "AWS CloudWatch metric {metric} published", 

        # Azure-style info logs
        "Azure VM {vm_id} provisioned successfully", 
        "Azure Blob Storage file {file_path} uploaded to container {container}", 
        "Azure SQL Database {db_name} backup completed", 
        "Azure App Service {service} deployed successfully", 
        "Azure Function {func_name} executed successfully", 
        "Azure Key Vault secret accessed by {user}", 
        "Azure Event Hub {hub} received message batch", 
        "Azure Kubernetes Service pod {pod} running", 
        "Azure Monitor metrics sent for {vm_id}", 
        "Azure Load Balancer probe succeeded for {server}", 
    ]

    # Expand with many variations (in real code you'd generate programmatically, but here we listed ~500+)
    # To save space here, assume we already filled templates to reach ~500 combined logs.

    for _ in range(num_samples // 3):
        # Error logs
        reason = np.random.choice(["timeout", "connection refused", "invalid credentials", "access denied", "connection reset"])
        module = np.random.choice(["auth_service", "data_processor", "api_gateway", "report_generator", "user_management"])
        line = np.random.randint(100, 1000)
        drive = np.random.choice(["/dev/sda1", "/mnt/data", "/var/log", "/opt/app"])
        user = np.random.choice(["admin", "guest", "dev", "system", "root"])
        service = np.random.choice(["payment_service", "notification_service", "logging_service", "monitoring_agent"])
        db_error_code = np.random.randint(1000, 9999)
        pid = np.random.randint(100, 9999)
        file_path = np.random.choice(["/etc/config.conf", "/var/log/syslog", "/app/data.json"])
        host = np.random.choice(["external-api.com", "internal-db.local", "message-queue.internal"])
        param_name = np.random.choice(["userId", "transactionId", "sessionId"])
        api_endpoint = np.random.choice(["/api/v1/users", "/api/v1/products", "/api/v1/orders"])

        error_log = np.random.choice(error_templates).format(
            reason=reason, module=module, line=line, drive=drive, user=user, service=service,
            db_error_code=db_error_code, pid=pid, file_path=file_path, host=host, param_name=param_name,
            instance_id=f"i-{np.random.randint(10000,99999)}", bucket="my-bucket", func_name="lambdaHandler", stack_name="stack1",
            table="users", task_id=f"task-{np.random.randint(100,999)}", pod=f"pod-{np.random.randint(10,99)}", vm_id=f"vm-{np.random.randint(100,999)}",
            container="container1", db_name="maindb", hub="hub1", partition=np.random.randint(1,5), queue="queue1", vault="vault1", api_endpoint=api_endpoint
        )
        logs.append(error_log)
        labels.append("incident")

        # Warning logs
        drive = np.random.choice(["/dev/sda1", "/mnt/data", "/var/log", "/opt/app"])
        server = np.random.choice(["web-01", "app-02", "db-01", "cache-03"])
        func = np.random.choice(["old_api", "legacy_method", "unoptimized_query"])
        api_endpoint = np.random.choice(["/api/v1/users", "/api/v1/products", "/api/v1/orders"])
        var_name = np.random.choice(["temp_var", "unused_param"])
        func_name = np.random.choice(["process_request", "calculate_metrics"])
        ip_address = f"192.168.{np.random.randint(0,255)}.{np.random.randint(0,255)}"
        domain = np.random.choice(["example.com", "internal.net"])
        host = np.random.choice(["external-api.com", "internal-db.local", "message-queue.internal"])

        warning_log = np.random.choice(warning_templates).format(
            drive=drive, server=server, func=func, api_endpoint=api_endpoint,
            var_name=var_name, func_name=func_name, ip_address=ip_address, domain=domain,
            instance_id=f"i-{np.random.randint(10000,99999)}", bucket="my-bucket", db_name="maindb", service="orderservice",
            metric="CPUUtilization", vm_id=f"vm-{np.random.randint(100,999)}", account="storage1", pod=f"pod-{np.random.randint(10,99)}",
            hub="hub1", vnet="vnet1", queue="queue1", vault="vault1", table=np.random.choice(["users", "orders", "metrics"]), host=host
        )
        logs.append(warning_log)
        labels.append("preventive_action")

        # Normal logs
        user = np.random.choice(["admin", "guest", "dev", "system", "monitor"])
        value = np.random.randint(0, 100)
        config_file = np.random.choice(["app.conf", "log4j.properties", "nginx.conf"])
        ip_address = f"10.0.{np.random.randint(0,255)}.{np.random.randint(0,255)}"
        func_name = np.random.choice(["init_module", "log_event", "send_heartbeat"])
        time_ms = np.random.randint(1, 50)
        table = np.random.choice(["users", "orders", "metrics"])

        normal_log = np.random.choice(normal_templates).format(
            user=user, value=value, config_file=config_file, ip_address=ip_address,
            func_name=func_name, time_ms=time_ms, instance_id=f"i-{np.random.randint(10000,99999)}",
            bucket="my-bucket", file_path="/data/file1.txt", db_name="maindb", stack_name="stack1",
            task_id=f"task-{np.random.randint(100,999)}", pod=f"pod-{np.random.randint(10,99)}", vm_id=f"vm-{np.random.randint(100,999)}",
            container="container1", service="orderservice", metric="CPUUtilization", hub="hub1", server="web-01", table=table
        )
        logs.append(normal_log)
        labels.append("normal")

    return pd.DataFrame({"log": logs, "label": labels})

if __name__ == "__main__":
    print("Generating synthetic log data...")
    df = generate_synthetic_logs(num_samples=10000)

    # Split the dataset into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        df["log"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )

    print("Training TF-IDF Vectorizer...")
    vectorizer = TfidfVectorizer(max_features=1000)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    print("Encoding labels...")
    label_encoder = LabelEncoder()
    y_train_encoded = label_encoder.fit_transform(y_train)
    y_test_encoded = label_encoder.transform(y_test)

    print("Training XGBoost model...")
    model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='mlogloss')
    model.fit(X_train_vec, y_train_encoded)

    print("Evaluating model...")
    y_pred_encoded = model.predict(X_test_vec)
    y_pred = label_encoder.inverse_transform(y_pred_encoded)
    print(classification_report(y_test, y_pred))

    print("Saving model, vectorizer, and label encoder...")
    with open("vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open("label_encoder.pkl", "wb") as f:
        pickle.dump(label_encoder, f)
    with open("xgboost_model.pkl", "wb") as f:
        pickle.dump(model, f)

    print("Model training complete. vectorizer.pkl, label_encoder.pkl, and xgboost_model.pkl saved.")
