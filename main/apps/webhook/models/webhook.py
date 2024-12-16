import hashlib
import hmac
import json
import logging
import secrets
import time
import uuid

from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import Company, User
from main.apps.core.utils.json_serializable import json_serializable
from main.apps.webhook.tasks import dispatch_webhook_event

logger = logging.getLogger(__name__)


class Event(models.Model):
    name = models.CharField(max_length=100, help_text="The name of the event.")
    type = models.CharField(max_length=32, unique=True, help_text="The unique type of the event.")

    def __str__(self):
        return self.name


class EventGroup(TimeStampedModel):
    name = models.CharField(max_length=50, help_text="The name of the event group.")
    slug = models.SlugField(help_text="The slug for the event group.")
    events = models.ManyToManyField(Event, help_text="The events associated with this group.")

    def save(self, **kwargs):
        if not self.id:
            self.slug = slugify(self.name)
        super(EventGroup, self).save(**kwargs)

    def __str__(self):
        return self.name


def generate_signing_secret(len: int = 32):
    return secrets.token_urlsafe(len)


class Webhook(TimeStampedModel):
    webhook_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True,
                                  help_text="The unique identifier for the webhook.")
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                help_text="The company associated with the webhook.")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, help_text="The user who created the webhook.")
    url = models.URLField(help_text="The URL where the webhook will send events.")
    events = models.ManyToManyField(Event, help_text="The events associated with this webhook.")
    groups = models.ManyToManyField(EventGroup, help_text="The event groups associated with this webhook.")
    signing_secret = models.CharField(max_length=255, default=generate_signing_secret,
                                      help_text="The signing secret for the webhook.")

    def __str__(self):
        return self.webhook_id.__str__()

    @staticmethod
    def get_subscribed_events(company: Company, user: User = None):
        """
        Returns a queryset of all unique events the company is subscribed to through its webhooks or event groups.
        Optionally, you can filter the webhooks by user.
        """
        webhooks = Webhook.objects.filter(company=company)
        if user:
            webhooks = webhooks.filter(created_by=user)

        events = Event.objects.filter(
            Q(webhook__in=webhooks) | Q(eventgroup__webhook__in=webhooks)
        ).distinct()
        return events

    @staticmethod
    def dispatch_event(company: Company, event_type, payload: dict, user: User = None):
        """
        Dispatches the specified event to all URLs associated with that event or event group for the given company.
        Optionally, you can filter the webhooks by user.
        """
        webhooks = Webhook.objects.filter(company=company)
        if user:
            webhooks = webhooks.filter(created_by=user)

        webhooks = webhooks.filter(
            Q(events__type=event_type) | Q(groups__events__type=event_type)
        ).distinct()

        dispatched_urls = []

        for webhook in webhooks:
            url = webhook.url
            signing_secret = webhook.signing_secret
            try:
                timestamp = int(time.time())
                serializable_payload = json_serializable(payload)
                webhook_payload = {
                    "event_type": event_type,
                    "payload": serializable_payload
                }
                json_payload = json.dumps(webhook_payload)
                signed_payload = f"{timestamp}.{json_payload}"

                # Generate the signature using the signing secret
                signature = hmac.new(signing_secret.encode('utf-8'), signed_payload.encode('utf-8'),
                                     hashlib.sha256).hexdigest()

                # Include the timestamp and signature in the headers
                headers = {
                    'Content-Type': 'application/json',
                    'Pangea-Signature': f"t={timestamp},v1={signature}"
                }

                dispatch_webhook_event.delay(url, webhook_payload, headers)
                dispatched_urls.append(url)
                logger.info(f"Webhook dispatched to {url} for event {event_type}")
            except Exception as e:
                logger.error(f"Error dispatching event to {url}: {e}")

        return dispatched_urls
