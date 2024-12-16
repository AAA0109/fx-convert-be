import logging

from celery import shared_task

from main.apps.account.models import Company
from main.apps.core.utils.slack import send_exception_to_slack
from main.apps.settlement.models import Beneficiary
from main.apps.settlement.services.beneficiary import BeneficiaryServiceFactory
from main.apps.settlement.services.wallet import WalletServiceFactory

logger = logging.getLogger(__name__)


@shared_task
def sync_beneficiary_to_brokers(beneficiary_id):
    beneficiary = Beneficiary.objects.get(pk=beneficiary_id)
    company = beneficiary.company
    factory = BeneficiaryServiceFactory(company=company)
    beneficiary_services = factory.create_beneficiary_services(
        currency=beneficiary.destination_currency)
    n_success_sync = 0
    errors = []
    for service in beneficiary_services:
        try:
            service.sync_beneficiary_to_broker(beneficiary)
            n_success_sync += 1
        except Exception as e:
            errors.append(f"* {service.broker.broker_provider}: {str(e)}")

    beneficiary.status = Beneficiary.Status.SYNCED \
        if n_success_sync == len(beneficiary_services) else Beneficiary.Status.PARTIALLY_SYNCED
    if n_success_sync == 0:
        beneficiary.status = Beneficiary.Status.DRAFT
    beneficiary.save(update_fields=['status'])

    if len(errors) > 0:
        logger.error('\n'.join(errors), exc_info=True)

    if len(beneficiary_services) > 0 and len(errors) >= len(beneficiary_services):
        raise Exception(f'Beneficiary sync failed for all configured broker. '
                        f'See beneficiary sync result on admin page for error detail')

    return beneficiary.status

@shared_task
def sync_delete_beneficiary_to_broker(beneficiary_id):
    beneficiary = Beneficiary.objects.get(pk=beneficiary_id)
    company = beneficiary.company
    factory = BeneficiaryServiceFactory(company=company)
    beneficiary_services = factory.create_beneficiary_services(
        currency=beneficiary.destination_currency)
    n_success_sync = 0
    errors = []
    for service in beneficiary_services:
        try:
            service.delete_beneficiary(beneficiary)
            n_success_sync += 1
        except Exception as e:
            errors.append(str(e))

    beneficiary.status = Beneficiary.Status.DELETED \
        if n_success_sync == len(beneficiary_services) else Beneficiary.Status.PARTIALLY_DELETED
    if n_success_sync == 0:
        beneficiary.status = Beneficiary.Status.DRAFT
    beneficiary.save(update_fields=['status'])

    if len(errors) > 0:
        logger.error('\n'.join(errors), exc_info=True)
    return beneficiary.status

@shared_task
def sync_wallet_from_brokers(company_id=None):
    try:
        if company_id:
            companies = Company.objects.filter(pk=company_id)
            if not companies.exists():
                logger.error(f"Company with ID {company_id} not found")
                return
        else:
            companies = Company.objects.all()

        for company in companies:
            wallet_services = WalletServiceFactory(company).create_wallet_services()
            total_synced = 0
            for wallet_service in wallet_services:
                try:
                    wallets = wallet_service.sync_wallets_from_broker()
                    total_synced += len(wallets)
                except Exception as e:
                    broker_provider = wallet_service.broker.broker_provider \
                        if hasattr(wallet_service, 'broker') else None
                    logger.error(f'Error syncing wallets from {broker_provider}'
                                 f' for {company.pk}|{company.name}: {str(e)}', exc_info=True)
            logger.info(f'{total_synced} Wallets successfully synced for company {company.pk}|{company.name}')
    except Exception as e:
        logger.exception(e)
        send_exception_to_slack(str(e))


@shared_task
def sync_beneficiary_from_brokers(company_id=None):
    try:
        if company_id:
            companies = Company.objects.filter(pk=company_id)
            if not companies.exists():
                logger.error()
                return
        else:
            companies = Company.objects.all()

        for company in companies:
            beneficiary_services = BeneficiaryServiceFactory(
                company).create_beneficiary_services()
            total_synced = 0
            for beneficiary_service in beneficiary_services:
                try:
                    beneficiaries = beneficiary_service.sync_beneficiaries_from_broker()
                    total_synced += len(beneficiaries)
                except Exception as e:
                    logger.error(f'Error syncing beneficiaries from {beneficiary_service.broker.broker_provider}'
                                 f' for {company.pk}|{company.name}: {str(e)}', exc_info=True)
            logger.info(f'{total_synced} Beneficiaries successfully synced for company {company.pk}|{company.name}')
    except Exception as e:
        logger.error(e, exc_info=True)
        send_exception_to_slack(str(e))
