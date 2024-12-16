import json
import logging


from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.dispatch import receiver

from main.apps.account.models import User, Account
from main.apps.billing.models.aum import Aum
from main.apps.billing.models.fee import Fee
from main.apps.hedge.models.company_hedge_action import CompanyHedgeAction
from main.apps.history.models.account_management import UserActivity
from main.apps.ibkr.models import DepositResult
from main.apps.billing.models import Payment


## Account Management Handlers
logger = logging.getLogger(__name__)
@receiver(post_save, sender=LogEntry)
def handle_log_entry_post_save(sender, instance: LogEntry, **kwargs):
    logger.debug(f"handle_log_entry_post_save: {instance} sender {sender}")
    try:
        content_type = instance.content_type
        logger.debug(f"content_type: {content_type}, object_id: {instance.object_id} model_class: {content_type.model_class()}")
        if content_type.model_class() not in [User, Account, Payment]:
            return
        if not instance.actor:
            logger.debug(f"Instance is missing an actor, ignoring")
            return
        if not instance.actor.company:
            logger.debug(f"User has no company, ignoring.")
            return
        changes = json.loads(instance.changes) if isinstance(instance.changes, str) else instance.changes
        entry = instance
        if content_type.model_class() == User:
            if entry.action == LogEntry.Action.CREATE:
                logger.debug(f"Creating UserAdded activity for {entry.object_repr}")
                UserActivity.objects.create(
                    log_entry=entry,
                    activity_type=UserActivity.ActivityType.UserAdded)
            elif entry.action == LogEntry.Action.UPDATE:
                if changes.get("password"):
                    logger.debug(f"Creating PasswordReset activity for {entry.object_repr}")
                    UserActivity.objects.create(
                        log_entry=entry,
                        activity_type=UserActivity.ActivityType.PasswordReset)
                elif changes.get("email"):
                    logger.debug(f"Creating EmailChanged activity for {entry.object_repr}")
                    UserActivity.objects.create(
                        log_entry=entry,
                        activity_type=UserActivity.ActivityType.EmailChanged)
        elif content_type.model_class() == Account:
            if entry.action == LogEntry.Action.CREATE:
                logger.debug(f"Creating AccountCreated activity for {entry.object_repr}")
                UserActivity.objects.create(
                    log_entry=entry,
                    activity_type=UserActivity.ActivityType.AccountCreated)
        elif content_type.model_class() == Payment:
            if entry.action == LogEntry.Action.CREATE:
                logger.debug(f"Creating PaymentCreated activity for {entry.object_repr}")
                UserActivity.objects.create(
                    log_entry=entry,
                    activity_type=UserActivity.ActivityType.PaymentCreated)
            elif entry.action == LogEntry.Action.UPDATE:
                logger.debug(f"Creating PaymentUpdated activity for {entry.object_repr}")
                if changes.get("payment_status"):
                    UserActivity.objects.create(
                        log_entry=entry,
                        activity_type=UserActivity.ActivityType.PaymentChanged)
    except ObjectDoesNotExist as e:
        logger.error(f"Could not find object for log entry {entry.id}: {e}")
