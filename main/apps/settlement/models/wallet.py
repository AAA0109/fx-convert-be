import uuid
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import Company
from main.apps.broker.models import Broker
from main.apps.currency.models import Currency


class Wallet(TimeStampedModel):
    wallet_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier of the wallet"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="wallets",
        help_text="The company the wallet belongs to"
    )
    broker = models.ForeignKey(
        Broker,
        on_delete=models.PROTECT,
        related_name="wallets",
        help_text="The broker the wallet is associated with"
    )
    broker_account_id = models.TextField(
        null=True,
        blank=True,
        help_text="The account identifier used by the broker for this account"
    )
    external_id = models.TextField(
        help_text="The external wallet identifier"
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        help_text="The currency of the wallet"
    )
    name = models.CharField(
        max_length=100,
        help_text="The name of the wallet",
        null=True,
        blank=True
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text="A description of the wallet"
    )
    account_number = models.CharField(
        max_length=100,
        help_text="The account number associated with the wallet",
        null=True
    )
    bank_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="The name of the bank associated with the wallet"
    )
    hidden = models.BooleanField(
        default=False,
        help_text="Whether the wallet is hidden, can be use for internal fee collection"
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The last time this wallet was synchronized with the broker's data"
    )

    class WalletStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")
        SUSPENDED = "suspended", _("Suspended")
        CLOSED = "closed", _("Closed")
        PENDING = "pending", _("Pending")

    status = models.CharField(
        max_length=20,
        choices=WalletStatus.choices,
        default=WalletStatus.ACTIVE,
        help_text="The status of the wallet"
    )

    class WalletType(models.TextChoices):
        SETTLEMENT = "settlement", _("Settlement")
        WALLET = "wallet", _("Wallet")
        VIRTUAL_ACCOUNT = 'virtual_account', _("Virtual Account")
        MANAGED = 'managed', _("Managed")

    type = models.CharField(
        max_length=20,
        choices=WalletType.choices,
        default=WalletType.WALLET,
        help_text="The type of the wallet"
    )

    class WalletAccountType(models.TextChoices):
        CHECKING = "checking", _("Checking")
        SAVING = "saving", _("Saving")

    account_type = models.CharField(
        max_length=20,
        choices=WalletAccountType.choices,
        null=True,
        blank=True,
        help_text="The type of the account"
    )

    class WalletMethod(models.TextChoices):
        RTP = 'rtp', _("RTP")
        EFT = 'eft', _('EFT')
        WIRE = 'wire', _('Wire')
        DRAFT = 'draft', _('Draft')

    method = models.CharField(
        max_length=10,
        choices=WalletMethod.choices,
        null=True,
        blank=True
    )

    nickname = models.CharField(
        max_length=100,
        null=True,
        help_text="Wallet nickname"
    )

    default = models.BooleanField(
        default=False,
        help_text="Set wallet as default funding account"
    )

    def __str__(self):
        return f"{self.name} - {self.account_number}"

    @staticmethod
    def get_wallets(company: Company, broker: Broker, currency: Currency, **kwargs) -> QuerySet:
        if company is None:
            raise ValidationError("Company cannot be none")
        if broker is None:
            raise ValidationError("Broker cannot be none")
        if currency is None:
            raise ValidationError("Currency cannot be none")
        return Wallet.objects.filter(company=company, broker=broker, currency=currency, **kwargs)

    @staticmethod
    def get_latest_balance(wallet: 'Wallet'):
        """
        Get the most recent WalletBalance for the given Wallet.

        Args:
            wallet (Wallet): The Wallet instance to get the balance for.

        Returns:
            WalletBalance: The most recent WalletBalance object, or None if no balance exists.
        """
        return WalletBalance.objects.filter(wallet=wallet).order_by('-timestamp').first()

class WalletBalance(models.Model):
    wallet = models.ForeignKey('Wallet', on_delete=models.CASCADE, related_name='balances')
    ledger_balance = models.DecimalField(max_digits=18, decimal_places=2, help_text="The total balance in the account")
    balance_held = models.DecimalField(max_digits=18, decimal_places=2,
                                       help_text="The amount of balance that is held or reserved")
    available_balance = models.DecimalField(max_digits=18, decimal_places=2,
                                            help_text="The balance that is available for use")
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        get_latest_by = 'timestamp'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.wallet.name} Balance at {self.timestamp}"
