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
    error_templates = [
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
    ]
    warning_templates = [
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
    ]
    normal_templates = [
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
    ]

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
        
        error_log = np.random.choice(error_templates).format(
            reason=reason, module=module, line=line, drive=drive, user=user, service=service,
            db_error_code=db_error_code, pid=pid, file_path=file_path, host=host, param_name=param_name
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

        warning_log = np.random.choice(warning_templates).format(
            drive=drive, server=server, func=func, api_endpoint=api_endpoint,
            var_name=var_name, func_name=func_name, ip_address=ip_address, domain=domain
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
        normal_log = np.random.choice(normal_templates).format(
            user=user, value=value, config_file=config_file, ip_address=ip_address,
            func_name=func_name, time_ms=time_ms
        )
        logs.append(normal_log)
        labels.append("normal")

    return pd.DataFrame({"log": logs, "label": labels})

if __name__ == "__main__":
    print("Generating synthetic log data...")
    df = generate_synthetic_logs(num_samples=10000)

    # Split the dataset into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        df["log"], df["label"], test_size=0.5, random_state=42, stratify=df["label"]
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
    with open("LLMlogs/vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open("LLMlogs/label_encoder.pkl", "wb") as f:
        pickle.dump(label_encoder, f)
    with open("LLMlogs/xgboost_model.pkl", "wb") as f:
        pickle.dump(model, f)

    print("Model training complete. vectorizer.pkl, label_encoder.pkl, and xgboost_model.pkl saved.")
