from django.db import models

# Create your models here.
from main.apps.account.models import User


class NotificationEvent(models.Model):
    class EventType(models.IntegerChoices):
        MARGIN = 1
        HEDGE = 2

    name = models.CharField(max_length=255, null=False)
    key = models.CharField(max_length=255, null=False)
    type = models.IntegerField(choices=EventType.choices)


class UserNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(NotificationEvent, on_delete=models.CASCADE)
    email = models.BooleanField(default=False)
    sms = models.BooleanField(default=False)
    phone = models.BooleanField(default=False)
