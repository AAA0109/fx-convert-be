import unittest
from datetime import datetime, timedelta
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from mock import Mock
from post_office.models import EmailTemplate

from main.apps.account.models import Company, Account, CashFlow, User
from main.apps.core.models import Config
from main.apps.corpay.models import DestinationAccountType, CorpaySettings, CurrencyDefinition
from main.apps.corpay.services.corpay import CorPayExecutionServiceFactory
from main.apps.corpay.signals.handlers import new_manual_forward
from main.apps.currency.models import Currency, FxPair
from main.apps.hedge.management.commands.execute_forwards import ForwardExecutionService
from main.apps.hedge.models import DraftFxForwardPosition
from main.apps.hedge.models import InstallmentCashflow


class ExecuteForwardsTest(TestCase):
    def test_trigger_manual_forward_signal(self):
        _, usd = Currency.create_currency('USD', 'USD', 'USD')
        _, php = Currency.create_currency('PHP', 'PHP', 'PHP')

        FxPair.objects.create(base_currency=php, quote_currency=usd)
        CurrencyDefinition.objects.create(
            currency_id=usd.pk,
            fwd_delivery_buying=True,
            fwd_delivery_selling=True
        )
        CurrencyDefinition.objects.create(
            currency_id=php.pk,
            fwd_delivery_buying=False,
            fwd_delivery_selling=False
        )

        rep = User.objects.create(
            password="babayaga",
            email="john@continental.com",
            first_name='John',
            last_name='Wick'

        )
        company = Company.objects.create(name='Test Company 1', currency=usd, status=Company.CompanyStatus.ACTIVE,
                                         rep=rep)
        account1 = Account.create_account(name="DUMMY-1", company=company)

        CorpaySettings.objects.create(
            company=company,
            client_code=12345,
            signature="Mock signature",
            average_volume=500,
            credit_facility=1000.0,
            max_horizon=365
        )

        for _ in range(2):
            cashflow = CashFlow.objects.create(
                account=account1,
                status=CashFlow.CashflowStatus.PENDING_ACTIVATION,
                name="mock_name",
                date=datetime.now() + timedelta(days=1),
                amount=1000.0,
                description="mock_description",
                calendar='NULL_CALENDAR',
                currency=php,

            )
            installment = InstallmentCashflow.objects.create(
                company=company,
                installment_name='installment_1',
            )

            DraftFxForwardPosition.objects.create(
                status=DraftFxForwardPosition.Status.PENDING_ACTIVATION,
                risk_reduction=100.0,
                origin_account="mock_origin_account",
                destination_account="mock_destination_account",
                destination_account_type=DestinationAccountType.W,
                cash_settle_account="mock_cash_settle_account",
                funding_account="mock_funding_account",
                is_cash_settle=False,
                purpose_of_payment="mock_purpose_of_payment",
                estimated_fx_forward_price=1.0,
                company=company,
                cashflow=cashflow,
                installment=installment,
            )

        Config.objects.create(
            value='teste@teste.com',
            path='corpay/order/email_recipients',
        )
        EmailTemplate.objects.create(
            name='company_non_sellable_forward',
            subject='New Non-sellable forward for {{company_name}}',
            content="""
        Hi {{company_rep}},

        Rate Request for {{company_name}}:
        {% for item in items %}
        Buy Currency: {{ item.currency_from.mnemonic }}
        Sell Currency: {{ item.currency_to.mnemonic }}
        Spot rate: {{ item.rate }}
        Amount: {{ item.amount_to|floatformat:"2g" }}
        Maturity Date: {{ item.date }}
        {% endfor %}
                """
        )

        # connecting the mock listener
        mock_receiver = Mock()
        new_manual_forward.connect(mock_receiver)

        # calling the command
        err = StringIO()
        call_command(
            "execute_forwards",
            company_id=company.pk,
            verbosity=2,
            stderr=err,
        )

        # testing the event trigger
        assert len(err.getvalue()) == 0
        assert mock_receiver.called, 'new_manual_forward event never triggered'
        assert mock_receiver.call_args.kwargs.get('sender') is ForwardExecutionService
        assert mock_receiver.call_args.kwargs.get('signal') is new_manual_forward
        assert mock_receiver.call_args.kwargs.get('company').pk is company.pk
        instances = mock_receiver.call_args.kwargs.get('instances')
        assert len(instances) == 2, 'do not collect all the manual forward instances'

        # testing the email
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == f'New Non-sellable forward for {company.name}'


if __name__ == '__main__':
    unittest.main()
