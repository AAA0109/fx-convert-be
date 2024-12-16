import logging

from django.dispatch import receiver
from hdlib.DateTime.Date import Date

from main.apps.account.models import CashFlow
from main.apps.ibkr.models import DepositResult
from main.apps.ibkr.signals import ibkr_deposit_processed
from main.apps.margin.services.what_if import DefaultWhatIfMarginInterface


logger = logging.getLogger(__name__)

@receiver(ibkr_deposit_processed)
def update_pending_margin_cashflows_handler(sender, instance: DepositResult, **kwargs):
    company = instance.funding_request.broker_account.company
    what_if_service = DefaultWhatIfMarginInterface()
    margin_detail = what_if_service.get_company_margin_health_including_pending(date=Date.today(), company=company)
    if margin_detail.get_margin_health().is_healthy:
        logger.debug(f"Company {instance.funding_request.broker_account.company} is healthy after deposit {instance}")
        logger.debug(f"Updating pending_margin cashflows to pending_activation")
        pending_margin_cashflows = CashFlow.get_company_pending_margin_cashflows(company=company)
        for cashflow in pending_margin_cashflows:
            logger.debug(f"Updating cashflow {cashflow} to pending_activation")
            cashflow.status = CashFlow.PENDING_ACTIVATION
            cashflow.save()
    else:
        logger.debug(f"Company {instance.funding_request.broker_account.company} is still not healthy after deposit {instance}")

