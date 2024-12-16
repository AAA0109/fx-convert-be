import logging

from celery import shared_task

from main.apps.corpay.services.beneficiary.cache import CorPayBeneficiaryCacheService
from main.apps.corpay.services.fxbalance.cache import CorPayFXBalanceCacheService
from main.apps.corpay.services.fxbalance.sweep import CorPayFXBalanceSweepService
from main.apps.corpay.services.settlement_account.cache import CorPaySettlementAccountCacheService

logger = logging.getLogger(__name__)

@shared_task(name="cache_corpay_fxaccount_balance")
def cache_corpay_fxaccount_balance(company_id=None):
    try:
        logger.debug(f"Running to cache CorPay FXAccount balance for (ID={company_id}).")
        service = CorPayFXBalanceCacheService()
        service.execute(company_id)
    except Exception as ex:
        logger.exception(ex)


@shared_task(name="cache_corpay_settlement_account")
def cache_corpay_settlement_account(company_id=None):
    try:
        logger.debug(f"Running to cache CorPay Settlement accounts for (ID={company_id}).")
        service = CorPaySettlementAccountCacheService()
        service.execute(company_id)
    except Exception as ex:
        logger.exception(ex)


@shared_task(name="cache_corpay_beneficiary")
def cache_corpay_beneficiary(company_id=None):
    try:
        logger.debug(f"Running to cache CorPay Beneficiaries for (ID={company_id})")
        service = CorPayBeneficiaryCacheService()
        service.execute(company_id)
    except Exception as ex:
        logger.exception(ex)


@shared_task(name='sweep_corpay_fxaccount_balance')
def sweep_corpay_fxaccount_balance(company_id=None):
    try:
        logger.debug(f"Running CorPay sweeping command for (ID={company_id})")
        service = CorPayFXBalanceSweepService()
        service.execute(company_id)
    except Exception as ex:
        logger.exception(ex)
