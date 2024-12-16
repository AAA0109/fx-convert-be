from abc import ABC
import logging
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

class SmsService(ABC):
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.messaging_service_sid = settings.TWILIO_MESSAGING_SERVICE_SID

    def send_sms(self, to: str, body: str):
        try:
            # Create message using messaging_service_sid
            message = self.client.messages.create(
                to=to,
                messaging_service_sid=self.messaging_service_sid,
                body=body
            )
            logger.info(f"Message sent successfully: {message.sid}")
            return message
        except TwilioRestException as e:
            logger.error(f"Twilio error: {e.code} - {e.msg}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        return None
