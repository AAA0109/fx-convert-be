import logging
from typing import List, Optional

import pytz
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.account.models import Account, Company, CashFlow
from main.apps.billing.models import Fee
from main.apps.billing.services.new_cash_fee import NewCashFeeService
from main.apps.core.utils.slack import SlackNotification
from main.apps.corpay.models.costs import TransactionCost
from main.apps.currency.models.currency import Currency
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

logger = logging.getLogger(__name__)


class DailyFeeService(object):
    fee_calculator = None
    __per_basis_point = 0.01

    def __init__(self, company_id: Optional[int]=None):
        self.company_id = company_id
        self.new_cash_fee_service = NewCashFeeService()
        self.slack = SlackNotification()

    def execute(self):
        now = Date.now()
        tz = pytz.timezone('US/Eastern')
        date = now.astimezone(tz)
        spot_fx_cache = FxSpotProvider().get_spot_cache()

        companies = Company.objects.filter(
            status__in=[Company.CompanyStatus.ACTIVE])
        if self.company_id:
            companies = companies.filter(pk=self.company_id)

        # loop through all companies
        for company in companies:
            accounts = Account.objects.filter(company=company)
            logging.info(
                f"Getting fees for company {company.pk} - {company.name}")

            fee_ids: List[int] = []

            cashflows = CashFlow.objects.filter(
                account__in=accounts, date__lte=date, status=CashFlow.CashflowStatus.ACTIVE)

            # loop through all company cashflows
            for cashflow in cashflows:

                # check if cashflow equal today
                if cashflow.date.date() == date.date():
                    # calculate apr
                    apr = self.__calculate_apr(
                        company=company, cashflow=cashflow, fx_spot_cache=spot_fx_cache)

                    # calculate fee
                    fee_amount = self.__calculate_fee(
                        company=company, cashflow=cashflow, apr=apr, fx_spot_cache=spot_fx_cache)

                    # append new settlement fee to fee table
                    fee = Fee(amount=fee_amount, incurred=cashflow.date, due=now, company=company,
                              status=Fee.Status.DUE, fee_type=Fee.FeeType.SETTLEMENT, cashflow=cashflow)
                    fee.save()
                    fee_ids.append(Fee.objects.last().id)

            # charge fees
            if len(fee_ids) > 0:
                fees = Fee.objects.filter(id__in=fee_ids)
                try:
                    # collect payment for fees
                    self.new_cash_fee_service.charge_fees(
                        company=company, fees=fees)
                    # If no exception was raised, payment was successfully collected for all new cashflow
                    updated_cashflows: List[CashFlow] = []
                    for fee in fees:
                        # set cashflow to pending activation
                        fee.cashflow.status = CashFlow.CashflowStatus.PENDING_ACTIVATION
                        updated_cashflows.append(fee.cashflow)
                    CashFlow.objects.bulk_update(updated_cashflows, ['status'])
                except Exception as e:
                    logging.error(e)
                    thread_ts = self.slack.send_text_message(
                        text=f"Failed to collect fees for company [{company.name} ({company.pk})]. "
                             f"Company has {fees.count()} new cashflow fees."
                    )
                    self.slack.send_mrkdwn_message(
                        text="Exception",
                        mrkdwn=f"```{e}```",
                        thread_ts=thread_ts
                    )

    def __calculate_fee(self, company: Company, cashflow: CashFlow, apr: float, fx_spot_cache: SpotFxCache) -> float:
        days_live = self.__get_days_live(cashflow=cashflow)
        amount = fx_spot_cache.convert_value(
            value=cashflow.amount, from_currency=cashflow.currency, to_currency=company.currency)
        return abs(days_live * apr * amount)

    def __get_days_live(self, cashflow: CashFlow) -> int:
        date_diff = cashflow.date - cashflow.created
        return date_diff.days

    def __calculate_apr(self, company: Company, cashflow: CashFlow, fx_spot_cache: SpotFxCache) -> Optional[float]:
        amount_in_usd = fx_spot_cache.convert_value(
            value=cashflow.amount, from_currency=cashflow.currency, to_currency=Currency.get_currency(currency="USD"))
        fx_forward_cost = TransactionCost.get_cost(company=company, notional_in_usd=amount_in_usd,
                                                   currency=cashflow.currency)
        return self.__per_basis_point * fx_forward_cost.cost_in_bps / 100
