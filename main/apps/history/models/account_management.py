import json
from enum import Enum
from typing import Optional, Dict, Any, Tuple, List

from auditlog.models import LogEntry
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import QuerySet
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import User, Account, Company
from main.apps.billing.models import Payment
from django.utils.translation import gettext_lazy as __


class UserActivity(TimeStampedModel):
    """
    This class records several activities that are filtered from the auditlog
    Ideally we should be able to filter the audit log directly, however unfortunately
    the complexity of filtering the audit log to only the events we care about is
    too high.  This is because the audit log is not designed to be filtered in this
    way because the changes are stored as a JSON object.

    The criteria of which elements get recorded here depends on signal hanlder:
    main/apps/history/signals/handlers.handle_log_entry_post_save
    """

    class ActivityType(models.TextChoices):
        UserAdded = "UserAdded", __("USER_ADDED")
        PasswordReset = "PasswordReset", __("PASSWORD_RESET")
        EmailChanged = "EmailChange", __("EMAIL_CHANGE")
        AccountCreated = "AccountCreated", __("ACCOUNT_CREATED")
        IbVerified = "IbVerified", __("IB_VERIFIED")
        CompanyVerified = "CompanyVerified", __("COMPANY_VERIFIED")
        PaymentCreated = "PaymentCreated", __("PAYMENT_CREATED")
        PaymentChanged = "PaymentChanged", __("PAYMENT_CHANGED")

    log_entry = models.ForeignKey(LogEntry, on_delete=models.CASCADE, null=True)
    activity_type = models.CharField(max_length=64, choices=ActivityType.choices, null=False, blank=False)

    @staticmethod
    def get_query_set(user: User) -> QuerySet['UserActivity']:
        return UserActivity.objects.filter(log_entry__actor=user).order_by("-log_entry__timestamp")

    @property
    def timestamp(self):
        return self.log_entry.timestamp

    @property
    def user(self) -> Optional[User]:
        return self.log_entry.actor

    @property
    def changes(self) -> Dict[str, Any]:
        entry_changes = json.loads(self.log_entry.changes)
        if self.activity_type == self.ActivityType.UserAdded:
            return {
                "email": entry_changes["email"][1],
            }
        elif self.activity_type == self.ActivityType.PasswordReset:
            return {
                "id": self.log_entry.object_id
            }
        elif self.activity_type == self.ActivityType.EmailChanged:
            return {
                "old_email": entry_changes["email"][0],
                "new_email": entry_changes["email"][1],
            }
        elif self.activity_type == self.ActivityType.AccountCreated:
            return {
                "id": self.log_entry.object_id,
            }
        elif self.activity_type == self.ActivityType.IbVerified:
            return {
                "id": self.log_entry.object_id,
            }
        elif self.activity_type == self.ActivityType.CompanyVerified:
            return {
                "id": self.log_entry.object_id,
            }

        elif self.activity_type == self.ActivityType.PaymentCreated:
            return {
                "id": self.log_entry.object_id,
            }
        elif self.activity_type == self.ActivityType.PaymentChanged:
            return {
                "id": self.log_entry.object_id,
            }

