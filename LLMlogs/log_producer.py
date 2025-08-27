from kafka import KafkaProducer
import json
import time
import random
from kafka.errors import NoBrokersAvailable

KAFKA_BROKER = 'kafka:9093'
KAFKA_TOPIC = 'logs'

producer = None
MAX_RETRIES = 20
RETRY_DELAY_SEC = 10

# Attempt to connect to Kafka with retry mechanism
for i in range(MAX_RETRIES):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(f"Successfully connected to Kafka after {i+1} attempts.")
        break
    except NoBrokersAvailable:
        print(f"Kafka brokers not available. Retrying in {RETRY_DELAY_SEC} seconds... (Attempt {i+1}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY_SEC)
    except Exception as e:
        print(f"An unexpected error occurred during Kafka connection: {e}")
        break

if producer is None:
    print("Failed to connect to Kafka after multiple retries. Exiting.")
    exit(1)

# ---------------- LOG GENERATOR ----------------
def generate_log():
    log_types = ["INFO", "WARNING", "ERROR", "DEBUG"]

    messages = {
        "INFO": [
            # Normal logs
            "INFO: User {user} logged in successfully.",
            "INFO: Data processed for report generation.",
            "INFO: System health check passed.",
            "INFO: New session started for user {user}.",
            "INFO: Application started successfully.",
            "INFO: Configuration loaded from {config_file}.",
            "INFO: Received request from IP {ip_address}.",
            # AWS info
            "AWS EC2 instance {instance_id} started successfully",
            "AWS S3 object {file_path} uploaded to bucket {bucket}",
            "AWS Lambda function {func_name} executed successfully",
            "AWS RDS instance {db_name} backup completed",
            "AWS CloudFormation stack {stack_name} deployed",
            "AWS DynamoDB table {table} created",
            # Azure info
            "Azure VM {vm_id} provisioned successfully",
            "Azure Blob Storage file {file_path} uploaded to container {container}",
            "Azure SQL Database {db_name} backup completed",
            "Azure App Service {service} deployed successfully",
            "Azure Function {func_name} executed successfully",
            "Azure Event Hub {hub} received message batch",
        ],
        "WARNING": [
            # Warnings
            "WARNING: Low disk space on {drive}",
            "WARNING: High CPU usage detected on {server}",
            "WARNING: Deprecated function {func} called",
            "WARNING: Failed to refresh cache. Using stale data.",
            # AWS warnings
            "AWS CloudWatch alarm triggered: {metric} usage above threshold",
            "AWS EC2 instance {instance_id} approaching memory limit",
            "AWS RDS instance {db_name} high latency warning",
            "AWS API Gateway rate limit approaching for {api_endpoint}",
            "AWS DynamoDB table {table} read capacity almost consumed",
            # Azure warnings
            "Azure Monitor detected high CPU usage on VM {vm_id}",
            "Azure Storage account {account} throttling requests",
            "Azure App Service {service} response time high",
            "Azure SQL Database {db_name} reaching DTU limit",
            "Azure Kubernetes Service pod {pod} restarting frequently",
        ],
        "ERROR": [
            # Errors
            "Database connection failed.",
            "NullPointerException in main service.",
            "Authentication failed for user 'admin'.",
            "Service 'payment' is unreachable.",
            # AWS errors
            "AWS EC2 instance {instance_id} failed to start due to {reason}",
            "AWS S3 bucket {bucket} access denied for user {user}",
            "AWS Lambda function {func_name} failed with error code {db_error_code}",
            "AWS RDS connection error: {reason}",
            "AWS API Gateway returned 500 Internal Server Error for {api_endpoint}",
            # Azure errors
            "Azure VM {vm_id} failed to allocate resources",
            "Azure Blob Storage container {container} access denied",
            "Azure SQL Database {db_name} connection failed",
            "Azure App Service {service} crashed unexpectedly",
            "Azure Function {func_name} execution timed out",
        ],
        "DEBUG": [
            "DEBUG: Variable 'x' value: {value}.",
            "DEBUG: Entering function 'process_data'.",
            "DEBUG: Function {func_name} completed in {time_ms}ms.",
            "Received request from IP {ip_address}.",
        ]
    }

    # Pick log type with weights
    log_type = random.choices(log_types, weights=[0.4, 0.4, 0.15, 0.05], k=1)[0]
    message_template = random.choice(messages[log_type])

    # Fill dynamic fields to make logs realistic
    message = message_template.format(
        user=random.choice(["admin", "guest", "dev", "system", "root"]),
        config_file=random.choice(["app.conf", "nginx.conf", "log4j.properties"]),
        ip_address=f"10.0.{random.randint(0,255)}.{random.randint(0,255)}",
        instance_id=f"i-{random.randint(10000,99999)}",
        bucket="my-bucket",
        func_name=random.choice(["lambdaHandler", "process_event", "init_module"]),
        db_error_code=random.randint(1000,9999),
        db_name=random.choice(["maindb", "analytics", "usersdb"]),
        stack_name=random.choice(["stack1", "stack2"]),
        table=random.choice(["users", "orders", "metrics"]),
        vm_id=f"vm-{random.randint(100,999)}",
        container=random.choice(["container1", "container2"]),
        service=random.choice(["auth-service", "payment-service", "orderservice"]),
        hub=random.choice(["hub1", "hub2"]),
        drive=random.choice(["/dev/sda1", "/mnt/data", "/var/log"]),
        server=random.choice(["web-01", "app-02", "db-01"]),
        func=random.choice(["legacy_method", "deprecatedFunc"]),
        api_endpoint=random.choice(["/api/v1/users", "/api/v1/orders"]),
        metric=random.choice(["CPUUtilization", "MemoryUsage"]),
        account=random.choice(["storage1", "storage2"]),
        pod=f"pod-{random.randint(10,99)}",
        reason=random.choice(["timeout", "connection refused", "access denied"]),
        value=random.randint(0,100),
        time_ms=random.randint(1,50),
        file_path=random.choice(['/var/log/app.log', '/home/user/data.csv', '/etc/config.json'])
    )

    log_entry = {
        "timestamp": time.time(),
        "level": log_type,
        "message": message,
        "service": random.choice(["auth-service", "data-pipeline", "web-app", "api-gateway"])
    }
    return log_entry

if __name__ == "__main__":
    print(f"Starting log producer for topic: {KAFKA_TOPIC}")
    print(f"Connecting to Kafka broker: {KAFKA_BROKER}")
    try:
        while True:
            log = generate_log()
            producer.send(KAFKA_TOPIC, log)
            print(f"Produced: {log}")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\nProducer stopped by user.")
    finally:
        producer.close()
