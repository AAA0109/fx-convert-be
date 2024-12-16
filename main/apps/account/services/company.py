from typing import Union
from main.apps.account.models.cashflow import CashFlow

from main.apps.account.models.company import Company
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.cashflow.models.generator import CashFlowGenerator
from main.apps.corpay.models.fx_forwards import ForwardQuote
from main.apps.oems.models.quote import Quote
from main.apps.oems.models.ticket import Ticket
from main.apps.payment.models.payment import Payment
from main.apps.settlement.models.beneficiary import Beneficiary
from main.apps.settlement.models.wallet import Wallet


class CompanyUtil:

    @staticmethod
    def clean_company_data_and_delete_company(company:Union[int, Company]):
        if isinstance(company, int):
            try:
                company = Company.objects.get(id=company)
            except Company.DoesNotExist:
                company = None

        if company:
            # Remove PROTECTED foreign key relations

            # Clean quote data for company
            Quote.objects.filter(company=company).delete()
            # Clean single cashflow data for company
            SingleCashFlow.objects.filter(company=company).delete()
            # Clean cashflow generator data for company
            CashFlowGenerator.objects.filter(company=company).delete()
            # Clean payment data for company
            Payment.objects.filter(company=company).delete()
            # Clean quote data for company
            Beneficiary.objects.filter(company=company).delete()
            # Clean wallet data for company
            Wallet.objects.filter(company=company).delete()
            # Clean forward quote data
            ForwardQuote.objects.filter(cashflow__account__company=company).delete()
            # Clean account cashflow data
            CashFlow.objects.filter(account__company=company).delete()
            # Clean ticket data for company
            Ticket.objects.filter(company=company).delete()

            company.delete()
