from auditlog.registry import auditlog
from django.db import models

from main.apps.account.models import Company


class Application(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='ibkr_application')
    external_id = models.CharField(max_length=60, null=False)
    user_id = models.IntegerField(null=False)
    username = models.CharField(max_length=11, null=False)
    account = models.CharField(max_length=60, null=False)
    entity = models.IntegerField(null=False)


auditlog.register(Application)
