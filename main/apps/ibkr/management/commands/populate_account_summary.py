import logging

from django.core.management.base import BaseCommand

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, Account
from main.apps.hedge.services.broker import BrokerService
from main.apps.ibkr.models import IbkrAccountSummary

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--company_id", type=int, help="Required: Company ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to fetch IBRK account summary."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    def handle(self, *args, **options):
        try:
            company_id = options["company_id"]

            company = Company.objects.get(pk=company_id)
            if company.status != Company.CompanyStatus.ACTIVE:
                raise Exception(f"Company (ID:{company_id}) is not active.")

            time = Date.now()
            logging.info(f"IBKR account summary population for (ID={company_id}) at time {time}.")

            broker_service = BrokerService()
            broker_account = broker_service.get_broker_for_company(
                company=company,
                account_type=Account.AccountType.LIVE)
            if not broker_account:
                logging.info(f"No broker account found for company (ID={company_id}).")
                return
            broker_account_name = broker_account.broker_account_name
            logging.info(f"Getting IBKR account summary for (ID={company_id}) at time {time}. Broker account: {broker_account_name}")
            ibkr_summary = broker_service.get_broker_account_summary(company=company, account_type=Account.AccountType.LIVE)
            if not ibkr_summary:
                logging.info(f"no IBKR account summary found for (ID={company_id}) at time {time}. Broker account: {broker_account_name}")
                return
            logging.info(f"Got IBKR account summary for (ID={company_id}) at time {time}.")
            logging.info(f"Saving account summary to DB for (ID={company_id}) at time {time}.")
            summary = IbkrAccountSummary.objects.create(
                broker_account=broker_account,
                account_type=ibkr_summary.account_type,
                cushion=ibkr_summary.cushion,
                look_ahead_next_change=ibkr_summary.look_ahead_next_change,
                accrued_cash=ibkr_summary.accrued_cash,
                available_funds=ibkr_summary.available_funds,
                buying_power=ibkr_summary.buying_power,
                equity_with_loan_value=ibkr_summary.equity_with_loan_value,
                excess_liquidity=ibkr_summary.excess_liquidity,
                full_init_margin_req=ibkr_summary.full_init_margin_req,
                full_maint_margin_req=ibkr_summary.full_maint_margin_req,
                full_available_funds=ibkr_summary.full_available_funds,
                full_excess_liquidity=ibkr_summary.full_excess_liquidity,
                gross_position_value=ibkr_summary.gross_position_value,
                init_margin_req=ibkr_summary.init_margin_req,
                maint_margin_req=ibkr_summary.maint_margin_req,
                look_ahead_available_funds=ibkr_summary.look_ahead_available_funds,
                look_ahead_excess_liquidity=ibkr_summary.look_ahead_excess_liquidity,
                look_ahead_init_margin_req=ibkr_summary.look_ahead_init_margin_req,
                look_ahead_maint_margin_req=ibkr_summary.look_ahead_maint_margin_req,
                net_liquidation=ibkr_summary.net_liquidation,
                sma=ibkr_summary.sma,
                total_cash_value=ibkr_summary.total_cash_value,
            )
            logging.info(f"Finished inserting summary (ID={summary.id}) to DB for (ID={company_id}) at time {time}.")
            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
