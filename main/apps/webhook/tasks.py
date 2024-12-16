from celery import shared_task
import requests
import logging

logger = logging.getLogger(__name__)

@shared_task
def dispatch_webhook_event(url: str, payload: dict, headers: dict):
    """
    Celery task to dispatch a webhook event to a given URL with a payload.

    Args:
        url (str): The URL to which the webhook event will be dispatched.
        payload (dict): The payload to be sent as part of the webhook event.
    """
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for any HTTP error status codes
        logger.debug(f"Webhook event dispatched successfully to {url}.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to dispatch webhook event to {url}. Error: {e}")
