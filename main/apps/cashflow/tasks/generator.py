from celery import shared_task
from main.apps.cashflow.models import CashFlowGenerator, SingleCashFlow
from main.apps.cashflow.services.generator import CashFlowGeneratorService


@shared_task
def create_single_cashflow_from_generator(generator: CashFlowGenerator):
    CashFlowGeneratorService.generate_single_cashflow(generator)
