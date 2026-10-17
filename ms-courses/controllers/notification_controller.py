import logging
import os
from notification_producer import notifs_rabbitmq
from models.constants import NOTIFICATION_TEMPLATES

# Check if we're in testing mode
NOTIF = not os.getenv("NOTIF")
USERS_URL = os.environ['DEV_USERS_URL'] if os.environ['ENVIRONMENT'] == 'development' else os.environ['MS_USERS_URL']

# Extra logger in case FastAPI is not enough
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

def send_notification(title: str, message: str, users: list[str], metadata: dict = None):  
    logging.info(f"Sending title \"{title}\" message \"{message}\" for users {users} with metadata {metadata}")
    if NOTIF:
        template_id: int = NOTIFICATION_TEMPLATES[title]
        if template_id:
            
            if notifs_rabbitmq and notifs_rabbitmq.enabled:
                notifs_rabbitmq.send_notification(template_id, title, message, users, metadata)
                logging.info(f"Notifications Queue: Notification sent successfully")
            else:
                logging.info("RabbitMQ producer mock: notification not sent")

        else:
            logging.warning(f"Notification template for title {title} not found") 
    else:
        logging.info(f"Message not sent (mocked)")
