import logging

from django.core.management import BaseCommand, CommandParser

from main.apps.account.models import Company, CashFlow
from main.apps.billing.models import Fee
from main.apps.billing.services.fee import FeeProviderService
from main.apps.billing.services.new_cash_fee import NewCashFeeService
from main.apps.core.utils.slack import SlackNotification
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

from hdlib.DateTime.Date import Date

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Django command to invoice backdated new cashflow fees for a company"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("--company_id", type=int, help="Optional: Company ID")

    def __init__(self):
        super().__init__()
        self.new_cash_fee_service = NewCashFeeService()
        self.slack = SlackNotification()
        self.fee_provider = FeeProviderService()
        self.spot_provider = FxSpotProvider()

    def handle(self, *args, **options):
        companies = Company.objects.filter(status__in=[Company.CompanyStatus.ACTIVE])
        if options['company_id']:
            companies = companies.filter(pk=options['company_id'])
        # loop through all companies

        for company in companies:
            cashflows = CashFlow.get_company_cashflows(company=company, status=CashFlow.CashflowStatus.ACTIVE)

            logger.debug(f"Company {company} has {len(cashflows)} active cashflows")

            cashflows_needing_fee = []

            for cashflow in cashflows:
                fees_for_cf = self.fee_provider.get_fees(company=company, cashflow=cashflow)
                if fees_for_cf:
                    fee_exists = False
                    for fee in fees_for_cf:
                        if fee.fee_type == Fee.FeeType.NEW_CASHFLOW:
                            fee_exists = True
                            break
                    # A fee has already been attached to this casfhlow
                    if fee_exists:
                        continue
                cashflows_needing_fee.append(cashflow)

            logger.debug(
                f"Company {company} has {len(cashflows_needing_fee)} cashflows that need a new cashflow fee")

            total_fee_amount = 0
            for cashflow in cashflows_needing_fee:
                cashflow_date = Date.from_datetime_date(cashflow.created)
                try:
                    spots = self.spot_provider.get_spot_cache(time=cashflow_date)

                    fee = NewCashFeeService().create_new_cashflow_fee(spot_fx_cache=spots, cashflow=cashflow,
                                                                      incurred=cashflow_date, due=cashflow_date)
                    total_fee_amount += fee.amount
                    logger.debug(f"Created fee of amount: {fee.amount}")
                except Exception as e:
                    logging.error(e)
                    thread_ts = self.slack.send_text_message(
                        text=f"Failed to retro invoice  company [{company.name} ({company.pk})] "
                             f"for cashflow {cashflow.id}"
                    )
                    self.slack.send_mrkdwn_message(
                        text="Exception",
                        mrkdwn=f"```{e}```",
                        thread_ts=thread_ts
                    )

            logger.debug(f"Done invoicing {len(cashflows_needing_fee)} new cashflow fees for Company {company}, "
                        f"total invoice: {total_fee_amount}")

