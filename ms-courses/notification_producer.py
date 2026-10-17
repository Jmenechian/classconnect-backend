import os
import json
import pika
import logging
from time import sleep
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

class RabbitMQProducer:
    def __init__(self, enabled: bool = True, rabbitmq_url: Optional[str] = None):
        self.enabled = enabled
        self.connection = None
        self.channel = None
        self.rabbitmq_url = rabbitmq_url
        
        if self.enabled and self.rabbitmq_url:
            self._connect()

    def _connect(self):
        """Establish connection with RabbitMQ server with retries"""
        if not self.enabled or not self.rabbitmq_url:
            return

        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                params = pika.URLParameters(self.rabbitmq_url)
                params.socket_timeout = 5
                params.heartbeat = 30
                params.connection_attempts = 3
                params.retry_delay = 1
                
                self.connection = pika.BlockingConnection(params)
                self.channel = self.connection.channel()
                self.channel.queue_declare(
                    queue='notifications',
                    durable=True,
                    arguments={'x-message-ttl': 86400000}  # 24h TTL
                )
                logging.info("Notifications Queue: Connected to RabbitMQ")
                return
            except Exception as e:
                retry_count += 1
                logging.warning(f"Notifications Queue: RabbitMQ connection attempt {retry_count} failed: {str(e)}")
                if retry_count < max_retries:
                    sleep(2 * retry_count)
        
        logging.error("Notifications Queue: Failed to connect to RabbitMQ after retries")
        self.enabled = False  # Desactivate if it couldn't connect

    def _ensure_connection(self):
        """Check connection and restablish if necessary"""
        if not self.enabled:
            return False
            
        if self.connection is None or self.connection.is_closed:
            logging.info("Notifications Queue: Reconnecting to RabbitMQ...")
            self._connect()
            
        return self.connection is not None and not self.connection.is_closed

    def send_notification(self, template_id: int, title: str, message: str, users: list[str], metadata: dict = None):
        """ Send notification through queue with retries"""
        if not self.enabled:
            logging.info("Notifications Queue: RabbitMQ disabled, notification not sent")
            return False

        notification = {
            "TemplateId": template_id,
            "Title": title,
            "Message": message,
            "Users": users,
            "Metadata": metadata or {} # optional
        }
        
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if not self._ensure_connection():
                    return False
                
                self.channel.basic_publish(
                    exchange='',
                    routing_key='notifications',
                    body=json.dumps(notification),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Persistent
                        content_type='application/json'
                    )
                )
                logging.info(f"Notifications Queue: Notification sent for users: {users}")
                return True
            except Exception as e:
                retry_count += 1
                logging.error(f"Notifications Queue: Error sending notification (attempt {retry_count}): {str(e)}")
                if retry_count < max_retries:
                    sleep(2 * retry_count)
                    self._connect()  # Reconnect before retry
        
        logging.error(f"Notifications Queue: Failed to send notification after {max_retries} attempts")
        return False
    

# RabbitMQ setup
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    logging.info("RabbitMQ: initializing queues for production")
    rabbitmq_url = os.getenv("CLOUDAMQP_URL")
    notifs_rabbitmq = RabbitMQProducer(enabled=True, rabbitmq_url=rabbitmq_url)
else:
    logging.info("RabbitMQ: using mock for development/testing")
    notifs_rabbitmq = RabbitMQProducer(enabled=False)