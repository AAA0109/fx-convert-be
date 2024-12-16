from main.apps.settlement.models import Beneficiary as BaseBeneficiary
from main.apps.settlement.models import Wallet as BaseWallet
from main.apps.payment.models import Payment as BasePayment


class Beneficiary(BaseBeneficiary):

    class Meta:
        proxy = True
        verbose_name_plural = 'Beneficiaries'


class Wallet(BaseWallet):

    class Meta:
        proxy = True


class Payment(BasePayment):

    class Meta:
        proxy = True
