import numpy as np
import pandas as pd

from typing import List, Optional

from main.apps.hedge.models import CompanyFxPosition, CompanyEvent
from hdlib.Hedge.Fx.HedgeAccount import HedgeMethod
from main.apps.hedge.models.hedgesettings import HedgeSettings
from main.apps.hedge.models import FxPosition, AccountHedgeRequest, CompanyHedgeAction, OMSOrderRequest
from main.apps.account.models import Company, Account, CashFlow
from main.apps.history.models import AccountSnapshot, CompanySnapshot
from main.apps.currency.models.currency import Currency
from main.apps.broker.models.broker import Broker, BrokerAccount
from main.apps.billing.models.aum import Aum
from main.apps.billing.models.fee import Fee
from main.apps.billing.models.fee_tier import FeeTier
from main.apps.billing.services.stripe.customer import StripeCustomerService
from main.apps.history.models.reconciliation_record import ReconciliationRecord

from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Date import Date
from main.apps.billing.services.stripe.payment import StripePaymentService, Card

logger = get_logger(level=logging.INFO)


class BacktestConfig(object):
    def __init__(self):
        pass

    @staticmethod
    def from_file(config_path: str):
        raise NotImplemented


class CompanyConfigurer(object):
    """ Create cashflows an put them into each of the test accounts """

    def __init__(self,
                 base_company_name: str,
                 cashflows_fpath: str,
                 ignore_unsupported_currencies: bool,
                 margin_budget: float = 2.e10,
                 ignore_cashflow_currencies: Optional[List[str]] = None,
                 are_cashflows_annualized: bool = False,
                 account_type: Account.AccountType = Account.AccountType.DEMO,
                 hedge_method: HedgeMethod = HedgeMethod.MIN_VAR,
                 setup_fees: bool = False):

        self._base_company_name = base_company_name
        self._cashflows_fpath = cashflows_fpath
        self._are_cashflows_annualized = are_cashflows_annualized  # if recurring cashflows are represented in annual amounts
        self._setup_fees = setup_fees

        self._ignore_unsupported_currencies = ignore_unsupported_currencies
        self._ignore_cashflow_currencies = ignore_cashflow_currencies or []  # Manually ignore these

        self._hedge_method = hedge_method
        self._margin_budget = margin_budget
        self._reduction_levels = (1.0, 0.85, 0.5, 0.25)
        self._companies: List[Company] = []
        self._company_names = [f"{base_company_name} @ No Risk",
                               f"{base_company_name} @ Low Risk",
                               f"{base_company_name} @ Med. Risk",
                               f"{base_company_name} @ High Risk"]

        self._accounts: List[Account] = []  # The accounts in same order as companies, one per company
        self._account_type = account_type

        # Hard coded
        self._domestic = "USD"
        self._broker = "IBKR"
        self._broker_account_name = "DU5241179"

    def configure_companies(self, clean_existing: bool = True) -> List[str]:
        self._create_companies(clean_existing)
        self._load_and_create_cashflows()
        self._add_settings()
        return self._company_names

    # noinspection DuplicatedCode
    def _clean_existing(self, company: Company):
        logger.debug(f"Cleaning out company {company}")
        # Delete existing accounts.
        delete_all = False

        CashFlow.objects.all().delete() if delete_all else CashFlow.objects.filter(account__company=company).delete()

        FxPosition.objects.all().delete() if delete_all else FxPosition.objects.filter(
            account__company=company).delete()

        CompanyFxPosition.objects.all().delete() if delete_all else CompanyFxPosition.objects.filter(
            company=company).delete()

        AccountHedgeRequest.objects.all().delete() if delete_all else AccountHedgeRequest.objects.filter(
            account__company=company).delete()

        CompanyHedgeAction.objects.all().delete() if delete_all else CompanyHedgeAction.objects.filter(
            company=company).delete()

        CompanyEvent.objects.all().delete() if delete_all else CompanyEvent.objects.filter(company=company).delete()

        OMSOrderRequest.objects.all().delete() if delete_all else OMSOrderRequest.objects.filter(
            company_hedge_action__company=company).delete()

        Fee.objects.all().delete() if delete_all else Fee.objects.filter(company=company).delete()

        FeeTier.objects.all().delete() if delete_all else FeeTier.objects.filter(company=company).delete()

        Aum.objects.all().delete() if delete_all else Aum.objects.filter(company=company).delete()

        AccountSnapshot.objects.all().delete() if delete_all else AccountSnapshot.objects.filter(
            account__company=company).delete()

        CompanySnapshot.objects.all().delete() if delete_all else CompanySnapshot.objects.filter(
            company=company).delete()

        ReconciliationRecord.objects.all().delete() if delete_all else ReconciliationRecord.objects.filter(
            company=company).delete()

        Account.objects.all().delete() if delete_all else Account.objects.filter(company=company).delete()

    def _create_companies(self, clean_existing: bool):
        self._companies = []
        self._accounts = []

        for company_name in self._company_names:
            logger.debug(f"Creating company: {company_name}")
            company = Company.create_company(company_name, currency=self._domestic)
            self._companies.append(company)

            if clean_existing:
                self._clean_existing(company=company)

            # Creating account for company
            logger.debug("Creating accounts")
            account = Account.get_or_create_account(name=f'{company}-Main Account',
                                                    company=company,
                                                    account_type=self._account_type)
            if self._setup_fees:
                # Add some fee tier
                if not FeeTier.has_tiers(company=company):
                    FeeTier.create_tier(company=company, tier_from=0., new_cash_fee_rate=0.01, aum_fee_rate=0.015)

                # Setup stripe
                stripe_customer = StripeCustomerService()
                stripe_customer.create_customer_for_company(company=company)
                stripe_payment = StripePaymentService()

                method = stripe_payment.create_card_payment_method(stripe_customer_id=company.stripe_customer_id,
                                                                   card=Card(number="4242424242424242",
                                                                             exp_month=10,
                                                                             exp_year=2029,
                                                                             cvc="314"))
                intent = stripe_payment.create_setup_intent_for_company_from_payment(company=company,
                                                                                     payment_method=method)

            # Setup the broker
            if self._account_type == Account.AccountType.LIVE:
                status, broker = Broker.create_broker(name=self._broker)
                BrokerAccount.delete_company_accounts(company=company)
                status, broker_account = BrokerAccount.create_account_for_company(
                    company=company,
                    broker=broker,
                    broker_account_name=self._broker_account_name,
                    account_type=BrokerAccount.AccountType.LIVE)
                logger.debug(status)

            self._accounts.append(account)

    def _load_and_create_cashflows(self):
        logger.debug("Loading cashflows")
        if len(self._accounts) == 0:
            raise RuntimeError("No accounts were created")

        cashflow_df = pd.read_csv(self._cashflows_fpath)

        logger.debug("Creating cashflow objects for each account")
        all_currencies = set()
        min_known_date = None

        date_fmt = '%m/%d/%Y'

        if 'first_pay_date' not in cashflow_df:
            cashflow_df['first_pay_date'] = cashflow_df['known_date']

        currencies = cashflow_df['currency'].unique()
        for currency in currencies:
            if currency in self._ignore_cashflow_currencies:
                pass
            if not Currency.get_currency(currency):
                logger.error(f"Unsupported currency: {currency}")
                if self._ignore_unsupported_currencies:
                    logger.debug("Skipping this currency, you configured to ignore this error")
                    continue
                raise ValueError("This currency is not supported")

        for index, row in cashflow_df.iterrows():
            known_date = Date.from_str(date=row['known_date'], fmt=date_fmt)
            first_pay_date = Date.from_str(date=row['first_pay_date'], fmt=date_fmt)

            min_known_date = known_date if not min_known_date else min(min_known_date, known_date)
            # max_end_date = end_date if not max_end_date else max(max_end_date, end_date)

            currency = row['currency']
            if currency in self._ignore_cashflow_currencies:
                continue
            if not Currency.get_currency(currency):
                continue  # We already checked at the beginning if user supports ignoring unsupported currencies

            all_currencies.add(currency)

            amount = row['amount']
            if np.isnan(amount):
                amount_in_domestic = row['amount_in_domestic']
                fx_rate = 0
                amount = amount_in_domestic * fx_rate
                raise NotImplementedError("TODO: handle case where currency is given as equiv amount in domestic")

            if self._are_cashflows_annualized:
                amount /= 12

            freq: str = row['frequency']

            end_date = None
            periodicity = None
            # If the frequency is empty everywhere, pandas assumes that everything in the column is a NaN float.
            if freq and not isinstance(freq, float):
                freq = freq.upper()
                if freq == "MONTHLY":
                    periodicity = "FREQ=MONTHLY;INTERVAL=1;BYDAY=WE"
                    end_date = Date.from_str(date=row['end_date'], fmt=date_fmt)
                else:
                    raise NotImplementedError(f"TODO: Add support for recurrin frequency: {freq}")

            # Add the cashflow to each account
            for account in self._accounts:
                CashFlow.create_cashflow(account=account,
                                         date=first_pay_date,
                                         end_date=end_date,
                                         currency=currency,
                                         amount=float(amount),
                                         periodicity=periodicity,
                                         status=CashFlow.CashflowStatus.ACTIVE)

        logger.debug(f"Finished adding cashflows in {len(all_currencies)} currencies:")
        logger.debug(",".join(all_currencies))

    def _add_settings(self):
        logger.debug("Adding settings to accounts")
        # Set or update hedge settings.
        for i in range(len(self._reduction_levels)):
            reduction = self._reduction_levels[i]
            logger.debug(f"Creating settings for account {self._accounts[i]} with reduction {reduction * 100}%")
            if self._hedge_method == HedgeMethod.MIN_VAR:
                HedgeSettings.create_or_update_settings(account=self._accounts[i],
                                                        margin_budget=self._margin_budget,
                                                        method="MIN_VAR",
                                                        custom={
                                                            'VolTargetReduction': reduction,
                                                            'VaR95ExposureRatio': None,
                                                            'VaR95ExposureWindow': None,
                                                        })
            elif self._hedge_method == HedgeMethod.PERFECT:
                HedgeSettings.create_or_update_settings(account=self._accounts[i],
                                                        margin_budget=self._margin_budget,
                                                        method="PERFECT",
                                                        custom={
                                                            'UniformRatio': reduction,
                                                        })
            else:
                raise NotImplementedError(f"No support for hedge method: {self._hedge_method}")
