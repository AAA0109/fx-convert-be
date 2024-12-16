import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from main.apps.ibkr.models import DepositResult, WithdrawResult
from main.apps.ibkr.signals import (
    ibkr_deposit_pending,
    ibkr_deposit_processed,
    ibkr_deposit_rejected,
    ibkr_withdraw_pending,
    ibkr_withdraw_processed,
    ibkr_withdraw_rejected
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DepositResult)
def handle_deposit_result_post_save(sender: DepositResult, instance: DepositResult, created, **kwargs):
    if created:
        ibkr_deposit_pending.send(sender=sender, instance=instance)
    if instance.status == DepositResult.Status.PROCESSED:
        ibkr_deposit_processed.send(sender=sender, instance=instance)
    if instance.status == DepositResult.Status.REJECTED:
        ibkr_deposit_rejected.send(sender=sender, instance=instance)


@receiver(post_save, sender=WithdrawResult)
def handle_withdraw_result_post_save(sender: WithdrawResult, instance: WithdrawResult, created, **kwargs):
    if created:
        ibkr_withdraw_pending.send(sender=sender, instance=instance)
    if instance.status == WithdrawResult.Status.PROCESSED:
        ibkr_withdraw_processed.send(sender=sender, instance=instance)
    if instance.status == WithdrawResult.Status.REJECTED:
        ibkr_withdraw_rejected.send(sender=sender, instance=instance)


@receiver(ibkr_deposit_pending)
def handle_ibkr_deposit_pending(sender, instance: DepositResult, **kwargs):
    pass


@receiver(ibkr_deposit_processed)
def handle_ibkr_deposit_processed(sender, instance: DepositResult, **kwargs):
    pass


@receiver(ibkr_deposit_rejected)
def handle_ibkr_deposit_rejected(sender, instance: DepositResult, **kwargs):
    pass


@receiver(ibkr_withdraw_pending)
def handle_ibkr_withdraw_pending(sender, instance: WithdrawResult, **kwargs):
    pass


@receiver(ibkr_withdraw_processed)
def handle_ibkr_withdraw_processed(sender, instance: WithdrawResult, **kwargs):
    pass


@receiver(ibkr_withdraw_rejected)
def handle_ibkr_withdraw_rejected(sender, instance: WithdrawResult, **kwargs):
    pass
