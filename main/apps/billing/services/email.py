import calendar
import logging
from abc import ABC
import datetime
from typing import Dict, Tuple, Iterable

from django.db.models import Sum, Min, Max
from django.db.models.functions import ExtractYear, ExtractMonth

from main.apps.account.models import Company
from main.apps.billing.models import Fee
from main.apps.billing.services.stripe.customer import StripeCustomerService
from main.apps.billing.services.stripe.payment import StripePaymentService

logger = logging.getLogger(__name__)


class InvoiceEmailService(ABC):
    def __init__(self, company: Company):
        self.company = company
        self.stripe_payment_service = StripePaymentService()
        self.stripe_customer_service = StripeCustomerService()
        self.fees = Fee.objects.filter(company=company, status=Fee.Status.DUE).order_by('incurred')

    def get_payment_last_four(self, company: Company) -> Tuple[str, bool]:
        setup_intent_id = company.stripe_setup_intent_id
        setup_intent = self.stripe_payment_service.retrieve_setup_intent(setup_intent_id=setup_intent_id)
        if setup_intent['payment_method'] is not None:
            payment_method = self.stripe_payment_service.retrieve_payment_method(
                payment_method_id=setup_intent['payment_method'])
            types = ['us_bank_account', 'card']
            for type in types:
                if type in payment_method:
                    return payment_method[type]['last4'], True
        return 'XXXX', False

    def get_context_data(self) -> Dict:
        output = {}
        if not self.fees.exists():
            return output
        account_number, has_payment = self.get_payment_last_four(company=self.company)
        output['account_number'] = account_number
        output['has_payment'] = has_payment
        output['min_date'] = self.get_min_date().strftime('%B, %Y')

        # commenting this out because we want to bill all unpaid fees
        # formatted_array = self.filter_current_month(self.fees)
        output['monthly_fees'] = self.generate_monthly_fees()
        output['total'] = self.sum_fees()
        output['title'] = "Upcoming Invoice"
        today = datetime.date.today()
        _, last_day = calendar.monthrange(today.year, today.month)
        paid_due_date = datetime.date(today.year, today.month, last_day)
        output['due_date'] = paid_due_date.strftime('%B %d, %Y')
        return output

    input_list = ['maintenance', 'new_cashflow', 'new_hedge']
    fee_type_map = {'maintenance': 'Maintenance',
                    'new_cashflow': 'New Cashflow', 'new_hedge': 'New Hedge'}

    def format_currency(self, amount: float):
        return "${:,.2f}".format(amount)

    def format_month_year(self, date: datetime):
        return datetime.strftime(date, '%B %Y')

    def filter_current_month(self, data: Iterable):
        today = datetime.date.today()
        current_month = today.month
        filtered_data = [d for d in data if d.incurred.month ==
                         current_month]
        return filtered_data

    def sum_fees(self):
        total = self.fees.aggregate(total=Sum('amount'))['total']
        return self.format_currency(total)

    def prepare_fees_array(self, fees: Iterable[Fee]):
        output = []
        for fee in fees:
            output.append({
                "incurred": fee.incurred.strftime("%m/%d/%y"),
                "fee_type": self.map_values(fee.fee_type, self.fee_type_map),
                "amount": self.format_currency(fee.amount)
            })
        return output

    def map_values(self, input: str, mapping_dict: dict):
        mapped_value = mapping_dict.get(input, input)
        return mapped_value

    def generate_monthly_fees(self):
        monthly_fees = (
            Fee.objects
            .annotate(year=ExtractYear('incurred'))
            .annotate(month=ExtractMonth('incurred'))
            .values('fee_type', 'year', 'month')
            .annotate(total_amount=Sum('amount'))
            .filter(company=self.company, status=Fee.Status.DUE)
            .order_by('fee_type', 'year', 'month')
        )
        output = {}
        for fee in monthly_fees:
            year = fee['year']
            month = fee['month']
            month_name = calendar.month_name[month]
            fee_type = fee['fee_type']
            total_amount = fee['total_amount']
            if year not in output:
                output[year] = {}
            if month_name not in output[year]:
                output[year][month_name] = {}
            if fee_type not in output[year][month_name]:
                output[year][month_name][fee_type] = []
            output[year][month_name][fee_type].append({
                "month": month,
                "month_name": month_name,
                "fee_type": self.map_values(fee_type, self.fee_type_map),
                "total": self.format_currency(total_amount)
            })

        return output

    def get_min_date(self):
        min_date = self.fees.aggregate(min_date=Min('incurred'))['min_date']
        return min_date
