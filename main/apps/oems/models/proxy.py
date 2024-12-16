from main.apps.cashflow.models import SingleCashFlow as BaseCashflow
from main.apps.cashflow.models import CashFlowGenerator as BaseCashflowGenerator
from main.apps.payment.models import Payment as BasePayment



class CashflowGenerator(BaseCashflowGenerator):

    class Meta:
        proxy = True
        verbose_name_plural = 'Cashflow Generators'


class Cashflow(BaseCashflow):

    class Meta:
        proxy = True


class Payment(BasePayment):

    class Meta:
        proxy = True
