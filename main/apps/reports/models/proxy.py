from django_celery_results.models import GroupResult as BaseGroupResult
from django_celery_results.models import TaskResult as BaseTaskResult
from auditlog.models import LogEntry as BaseLogEntry

from main.apps.core.models import Config as BaseConfig
from main.apps.core.models import VendorOauth as BaseVendorOauth


class GroupResult(BaseGroupResult):

    class Meta:
        proxy = True


class TaskResult(BaseTaskResult):

    class Meta:
        proxy = True


class Config(BaseConfig):

    class Meta:
        proxy = True


class VendorOauth(BaseVendorOauth):

    class Meta:
        proxy = True


class LogEntry(BaseLogEntry):

    class Meta:
        proxy = True
        verbose_name_plural = 'Log Entries'
