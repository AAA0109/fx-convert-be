from django.db import models
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import User, Company


class ApiLogBase(TimeStampedModel):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    company = models.ForeignKey(Company, null=True, on_delete=models.SET_NULL)

    class Meta:
        abstract = True


class ApiRequestLog(ApiLogBase):
    url = models.URLField()
    method = models.CharField(max_length=10)
    payload = models.TextField(null=True, blank=True)


class ApiResponseLog(ApiLogBase):
    request_log = models.OneToOneField(ApiRequestLog, on_delete=models.CASCADE)
    response = models.TextField(null=True, blank=True)
