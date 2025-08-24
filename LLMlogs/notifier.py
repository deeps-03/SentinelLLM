"""
Notifier Service

This service consumes classified logs and anomalies, and sends notifications
via email (SMTP) and Microsoft Teams webhooks based on classification rules
and anomaly thresholds.
"""

import os
import json
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class NotifierService:
    """Notification service for log alerts and anomalies."""
    
    def __init__(self):
        self.config = {
            'kafka_broker': os.getenv('KAFKA_BROKER', 'kafka:9093'),
            'classified_logs_topic': os.getenv('CLASSIFIED_LOGS_TOPIC', 'classified-logs'),
            'anomalies_topic': os.getenv('ANOMALIES_TOPIC', 'anomalies'),
            
            # Email configuration
            'smtp_host': os.getenv('SMTP_HOST'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_username': os.getenv('SMTP_USERNAME'),
            'smtp_password': os.getenv('SMTP_PASSWORD'),
            'smtp_use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
            'email_from': os.getenv('EMAIL_FROM'),
            'email_recipients': [email.strip() for email in os.getenv('EMAIL_RECIPIENTS', '').split(',') if email.strip()],
            
            # Teams configuration
            'teams_webhook_url': os.getenv('TEAMS_WEBHOOK_URL'),
            
            # Alert configuration
            'anomaly_threshold': float(os.getenv('ANOMALY_THRESHOLD', '0.8')),
            'dedup_window_minutes': int(os.getenv('DEDUP_WINDOW_MINUTES', '15')),
            'send_preventive_emails': os.getenv('SEND_PREVENTIVE_EMAILS', 'false').lower() == 'true',
            'grafana_base_url': os.getenv('GRAFANA_BASE_URL', 'http://localhost:3000'),
            
            # Kafka configuration
            'max_retries': int(os.getenv('MAX_RETRIES', '5')),
            'retry_delay': int(os.getenv('RETRY_DELAY_SECONDS', '5'))
        }
        
        # Validate configuration
        self._validate_config()
        
        # Initialize consumers
        self.classified_logs_consumer = None
        self.anomalies_consumer = None
        
        # Deduplication tracking
        self.alert_history = defaultdict(list)
        
        # Initialize services
        self._initialize_kafka_consumers()
    
    def _validate_config(self):
        """Validate required configuration parameters."""
        # Check if at least one notification method is configured
        has_email = all([
            self.config['smtp_host'],
            self.config['smtp_username'],
            self.config['smtp_password'],
            self.config['email_from'],
            self.config['email_recipients']
        ])
        
        has_teams = bool(self.config['teams_webhook_url'])
        
        if not (has_email or has_teams):
            raise ValueError("At least one notification method (email or Teams) must be configured")
        
        if has_email:
            logger.info(f"Email notifications configured: {len(self.config['email_recipients'])} recipients")
        if has_teams:
            logger.info("Teams notifications configured")
    
    def _initialize_kafka_consumers(self):
        """Initialize Kafka consumers with retries."""
        for attempt in range(self.config['max_retries']):
            try:
                # Classified logs consumer
                self.classified_logs_consumer = KafkaConsumer(
                    self.config['classified_logs_topic'],
                    bootstrap_servers=[self.config['kafka_broker']],
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    group_id='notifier-classified-logs',
                    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
                )
                
                # Anomalies consumer
                self.anomalies_consumer = KafkaConsumer(
                    self.config['anomalies_topic'],
                    bootstrap_servers=[self.config['kafka_broker']],
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    group_id='notifier-anomalies',
                    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
                )
                
                logger.info(f"Successfully connected to Kafka at {self.config['kafka_broker']}")
                return
                
            except NoBrokersAvailable:
                logger.warning(f"Kafka brokers not available. Retrying in {self.config['retry_delay']} seconds... (Attempt {attempt + 1}/{self.config['max_retries']})")
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'])
                else:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error connecting to Kafka: {e}")
                raise
    
    def _generate_alert_id(self, alert_data):
        """Generate a unique ID for deduplication."""
        # Create hash based on key alert properties
        key_data = {
            'service': alert_data.get('service', ''),
            'host': alert_data.get('host', ''),
            'classification': alert_data.get('classification', ''),
            'alert_type': alert_data.get('alert_type', ''),
            'message_hash': hashlib.md5(alert_data.get('message', '').encode()).hexdigest()[:8]
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def _is_duplicate_alert(self, alert_id):
        """Check if alert is a duplicate within the dedup window."""
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=self.config['dedup_window_minutes'])
        
        # Clean old entries
        self.alert_history[alert_id] = [
            timestamp for timestamp in self.alert_history[alert_id]
            if timestamp > cutoff_time
        ]
        
        # Check if alert exists in recent history
        if self.alert_history[alert_id]:
            return True
        
        # Add current alert to history
        self.alert_history[alert_id].append(now)
        return False
    
    def _send_email(self, subject, body, html_body=None):
        """Send email notification."""
        if not all([self.config['smtp_host'], self.config['smtp_username'], 
                   self.config['smtp_password'], self.config['email_from']]):
            logger.warning("Email configuration incomplete, skipping email notification")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config['email_from']
            msg['To'] = ', '.join(self.config['email_recipients'])
            
            # Add text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            server = smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port'])
            if self.config['smtp_use_tls']:
                server.starttls()
            server.login(self.config['smtp_username'], self.config['smtp_password'])
            server.send_message(msg, to_addrs=self.config['email_recipients'])
            server.quit()
            
            logger.info(f"Email sent successfully to {len(self.config['email_recipients'])} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _send_teams_message(self, title, text, color="warning", facts=None):
        """Send Microsoft Teams notification."""
        if not self.config['teams_webhook_url']:
            logger.warning("Teams webhook URL not configured, skipping Teams notification")
            return False
        
        try:
            # Create Teams message payload
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": color,
                "title": title,
                "text": text
            }
            
            # Add facts if provided
            if facts:
                payload["sections"] = [{
                    "facts": [{"name": k, "value": v} for k, v in facts.items()]
                }]
            
            # Add action buttons
            payload["potentialAction"] = [{
                "@type": "OpenUri",
                "name": "View in Grafana",
                "targets": [{
                    "os": "default",
                    "uri": self.config['grafana_base_url']
                }]
            }]
            
            # Send request
            response = requests.post(
                self.config['teams_webhook_url'],
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info("Teams message sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Teams message: {e}")
            return False
    
    def _format_classified_log_alert(self, log_data):
        """Format alert for classified log."""
        classification = log_data.get('classification', 'unknown')
        service = log_data.get('service', 'unknown')
        host = log_data.get('host', 'unknown')
        message = log_data.get('message', '')
        suggestions = log_data.get('suggestions', None)
        timestamp = log_data.get('timestamp', time.time())
        
        # Format timestamp
        dt = datetime.fromtimestamp(timestamp / 1000 if timestamp > 1e10 else timestamp)
        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        subject = f"🚨 {classification.upper()} Alert: {service} on {host}"
        
        # Plain text body
        body = f"""
Alert Details:
- Classification: {classification.upper()}
- Service: {service}
- Host: {host}
- Timestamp: {formatted_time}
- Message: {message}
        """.strip()

        if suggestions:
            body += f"\n\nSuggestions:\n{suggestions}"

        body += f"\n\nThis alert was generated by SentinelLLM.\nView dashboard: {self.config['grafana_base_url']}"
        
        # HTML body
        html_body = f"""
<html>
<body>
<h2 style=\"color: {'red' if classification == 'incident' else 'orange'};\">
    🚨 {classification.upper()} Alert
</h2>
<p><strong>Service:</strong> {service}</p>
<p><strong>Host:</strong> {host}</p>
<p><strong>Timestamp:</strong> {formatted_time}</p>
<p><strong>Classification:</strong> {classification.upper()}</p>
<p><strong>Message:</strong></p>
<blockquote style=\"background-color: #f0f0f0; padding: 10px; border-left: 3px solid #ccc;\">
{message}
</blockquote>
        """.strip()

        if suggestions:
            html_body += f"""
<p><strong>Suggestions:</strong></p>
<blockquote style=\"background-color: #e6f7ff; padding: 10px; border-left: 3px solid #1890ff;\">
{suggestions}
</blockquote>
            """.strip()

        html_body += f"""
<hr>
<p>This alert was generated by SentinelLLM.</p>
<p><a href=\"{self.config['grafana_base_url']}\">View Dashboard</a></p>
</body>
</html>
        """.strip()
        
        return subject, body, html_body
    
    def _format_anomaly_alert(self, anomaly_data):
        """Format alert for anomaly detection."""
        anomaly_type = anomaly_data.get('type', 'unknown')
        score = anomaly_data.get('score', 0)
        details = anomaly_data.get('details', '')
        timestamp = anomaly_data.get('timestamp', time.time())
        
        # Format timestamp
        dt = datetime.fromtimestamp(timestamp / 1000 if timestamp > 1e10 else timestamp)
        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        subject = f"🔍 Anomaly Detected: {anomaly_type} (Score: {score:.2f})"
        
        # Plain text body
        body = f"""
Anomaly Alert:
- Type: {anomaly_type}
- Anomaly Score: {score:.2f}
- Threshold: {self.config['anomaly_threshold']}
- Timestamp: {formatted_time}
- Details: {details}

This anomaly was detected by SentinelLLM.
View dashboard: {self.config['grafana_base_url']}
        """.strip()
        
        # HTML body
        html_body = f"""
<html>
<body>
<h2 style=\"color: red;\">🔍 Anomaly Detected</h2>
<p><strong>Type:</strong> {anomaly_type}</p>
<p><strong>Anomaly Score:</strong> {score:.2f}</p>
<p><strong>Threshold:</strong> {self.config['anomaly_threshold']}</p>
<p><strong>Timestamp:</strong> {formatted_time}</p>
<p><strong>Details:</strong></p>
<blockquote style=\"background-color: #fff5f5; padding: 10px; border-left: 3px solid #ff6b6b;\">
{details}
</blockquote>
<hr>
<p>This anomaly was detected by SentinelLLM.</p>
<p><a href=\"{self.config['grafana_base_url']}\">View Dashboard</a></p>
</body>
</html>
        """.strip()
        
        return subject, body, html_body
    
    def _process_classified_log(self, log_data):
        """Process classified log and send appropriate notifications."""
        classification = log_data.get('classification', '').lower()
        
        # Prepare alert data for deduplication
        alert_data = {
            'alert_type': 'classified_log',
            'service': log_data.get('service', 'unknown'),
            'host': log_data.get('host', 'unknown'),
            'classification': classification,
            'message': log_data.get('message', '')
        }
        
        alert_id = self._generate_alert_id(alert_data)
        
        # Check for duplicate
        if self._is_duplicate_alert(alert_id):
            logger.debug(f"Duplicate alert suppressed: {alert_id}")
            return
        
        # Determine notification actions based on classification
        send_email = False
        send_teams = False
        
        if classification == 'incident':
            send_email = True
            send_teams = True
        elif classification == 'preventive_action':
            send_email = self.config['send_preventive_emails']
            send_teams = True
        else:
            # Don't send notifications for 'normal' classification
            return
        
        # Format alert
        subject, body, html_body = self._format_classified_log_alert(log_data)
        
        # Send notifications
        if send_email:
            self._send_email(subject, body, html_body)
        
        if send_teams:
            color = "attention" if classification == 'incident' else "warning"
            facts = {
                "Service": log_data.get('service', 'unknown'),
                "Host": log_data.get('host', 'unknown'),
                "Classification": classification.upper()
            }
            if 'suggestions' in log_data:
                facts["Suggestions"] = log_data['suggestions']

            self._send_teams_message(subject, body, color, facts)
        
        logger.info(f"Processed {classification} alert for {alert_data['service']}")
    
    def _process_anomaly(self, anomaly_data):
        """Process anomaly and send appropriate notifications."""
        score = anomaly_data.get('score', 0)
        
        # Check if anomaly exceeds threshold
        if score < self.config['anomaly_threshold']:
            logger.debug(f"Anomaly score {score} below threshold {self.config['anomaly_threshold']}")
            return
        
        # Prepare alert data for deduplication
        alert_data = {
            'alert_type': 'anomaly',
            'service': 'anomaly-detector',
            'host': 'system',
            'classification': 'anomaly',
            'message': anomaly_data.get('details', f"Anomaly score: {score}")
        }
        
        alert_id = self._generate_alert_id(alert_data)
        
        # Check for duplicate
        if self._is_duplicate_alert(alert_id):
            logger.debug(f"Duplicate anomaly alert suppressed: {alert_id}")
            return
        
        # Format alert
        subject, body, html_body = self._format_anomaly_alert(anomaly_data)
        
        # Send both email and Teams for anomalies
        self._send_email(subject, body, html_body)
        
        facts = {
            "Anomaly Type": anomaly_data.get('type', 'unknown'),
            "Score": f"{score:.2f}",
            "Threshold": f"{self.config['anomaly_threshold']}"
        }
        self._send_teams_message(subject, body, "attention", facts)
        
        logger.info(f"Processed anomaly alert with score {score:.2f}")
    
    def run(self):
        """Main notification loop."""
        logger.info("Starting Notifier Service")
        logger.info(f"Deduplication window: {self.config['dedup_window_minutes']} minutes")
        logger.info(f"Anomaly threshold: {self.config['anomaly_threshold']}")
        
        try:
            while True:
                # Process classified logs
                for message in self.classified_logs_consumer:
                    try:
                        log_data = message.value
                        self._process_classified_log(log_data)
                    except Exception as e:
                        logger.error(f"Error processing classified log: {e}")
                    
                    # Non-blocking check for anomalies
                    break
                
                # Process anomalies
                for message in self.anomalies_consumer:
                    try:
                        anomaly_data = message.value
                        self._process_anomaly(anomaly_data)
                    except Exception as e:
                        logger.error(f"Error processing anomaly: {e}")
                    
                    # Non-blocking check for classified logs
                    break
                
                # Small sleep to prevent tight loop
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Notifier Service stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up Notifier Service...")
        
        if self.classified_logs_consumer:
            try:
                self.classified_logs_consumer.close()
                logger.info("Classified logs consumer closed")
            except Exception as e:
                logger.error(f"Error closing classified logs consumer: {e}")
        
        if self.anomalies_consumer:
            try:
                self.anomalies_consumer.close()
                logger.info("Anomalies consumer closed")
            except Exception as e:
                logger.error(f"Error closing anomalies consumer: {e}")
        
        logger.info("Notifier Service shutdown complete")


def main():
    """Main entry point."""
    try:
        notifier = NotifierService()
        notifier.run()
    except Exception as e:
        logger.error(f"Failed to start Notifier Service: {e}")
        exit(1)


if __name__ == "__main__":
    main()