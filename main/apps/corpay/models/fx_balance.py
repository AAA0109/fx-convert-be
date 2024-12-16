from django.db import models
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import Company
from main.apps.currency.models import Currency


class FXBalanceAccount(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)
    description = models.CharField(max_length=100)
    account = models.CharField(max_length=60)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False)
    ledger_balance = models.DecimalField(max_digits=20, decimal_places=4)
    balance_held = models.DecimalField(max_digits=20, decimal_places=4)
    available_balance = models.DecimalField(max_digits=20, decimal_places=4)
    account_number = models.CharField(max_length=60)
    client_code = models.CharField(max_length=60)
    client_division_id = models.IntegerField()

    def __str__(self):
        return self.account_number


class FXBalanceAccountSettlementInstruction(models.Model):
    fx_balance_account = models.OneToOneField(FXBalanceAccount, on_delete=models.CASCADE,
                                                related_name='settlement_instructions')
    is_na_associated = models.BooleanField(default=False)
    incoming_account_number = models.CharField(max_length=60)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False)
    curr_name = models.CharField(max_length=50)
    is_iban = models.BooleanField(default=False)
    bene_info = models.TextField()
    bank_name = models.CharField(max_length=100)
    bank_address = models.TextField()
    bank_swift = models.CharField(max_length=60)

    def __str__(self):
        return self.curr_name


class FXBalance(TimeStampedModel):
    class FXBalanceStatus(models.TextChoices):
        NEW = ('new', 'New')
        PENDING = ('pending', 'Pending Approval')
        APPROVED = ('approved', 'Approved')
        PROCESSING = ('processing', 'Processing')
        COMPLETE = ('complete', 'Complete')
        ERROR = ('error', 'Error')

    status = models.CharField(choices=FXBalanceStatus.choices, max_length=10)
    account_number = models.CharField(max_length=60)
    date = models.DateField()
    order_number = models.CharField(max_length=60)
    amount = models.FloatField()
    debit_amount = models.FloatField()
    credit_amount = models.FloatField()
    is_posted = models.BooleanField()
    balance = models.FloatField()
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)


class FXBalanceDetail(TimeStampedModel):
    transaction_id = models.IntegerField()
    order_number = models.CharField(max_length=60)
    identifier = models.CharField(max_length=60)
    name = models.CharField(max_length=60)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False)
    amount = models.FloatField()
    date = models.DateField()
    fx_balance = models.ForeignKey(FXBalance, on_delete=models.CASCADE, null=False, related_name='details')

    class Meta:
        unique_together = ('fx_balance', 'order_number', 'transaction_id')
