import os
import sys
from hdlib.DateTime.Date import Date
from scripts.lib.only_local import only_allow_local


def add_broker_account(company):
    from main.apps.account.models import Broker, BrokerAccount

    status, broker = Broker.create_broker(name="IBKR")
    BrokerAccount.delete_company_accounts(company=company)
    BrokerAccount.create_account_for_company(company=company,
                                             broker=broker,
                                             broker_account_name="DU5241179",
                                             account_type=BrokerAccount.AccountType.LIVE)


def create_company_I(account_type):
    from main.apps.hedge.models.hedgesettings import HedgeSettings
    from main.apps.account.models.account import Account
    from main.apps.account.models.cashflow import CashFlow
    from main.apps.account.models.company import Company

    ref_date = Date.today()

    # =======================
    # Case I: Company with 1 Account, 1 Currency, Only Raw Cashflows (In one direction)
    # =======================
    company = Company.create_company(name="EOD_Test_1Acct_1Curr_RawCash", currency="USD")

    if account_type == Account.AccountType.LIVE:
        add_broker_account(company=company)

    name = "Main Account"
    try:
        Account.remove_account(account_name=name, company=company)
    except Exception:
        pass
    account = Account.get_or_create_account(name=name, company=company,
                                            account_type=account_type)

    # =======================
    # Add some cashflows to the account
    # =======================
    for date in (ref_date + 30, ref_date + 60, ref_date + 120, ref_date + 360):
        for currency in ("GBP",):
            CashFlow.create_cashflow(account=account,
                                     date=date,
                                     currency=currency,
                                     amount=1024.25,
                                     status=CashFlow.CashflowStatus.ACTIVE)

    # =======================
    # Add hedge settings
    # =======================
    HedgeSettings.create_or_update_settings(account=account,
                                            margin_budget=2.e10,
                                            method="MIN_VAR",
                                            custom={'VolTargetReduction': 0.95})


def create_company_II(account_type):
    from main.apps.hedge.models.hedgesettings import HedgeSettings
    from main.apps.account.models import Account
    from main.apps.account.models.cashflow import CashFlow
    from main.apps.account.models.company import Company

    ref_date = Date.today()

    # =======================
    # Case II: Company with 1 Account, Multi Currency, Mixed Cashflow types in both directions
    # =======================
    company = Company.create_company(name="EOD_Test_1Acct_XCurr", currency="USD")

    if account_type == Account.AccountType.LIVE:
        add_broker_account(company=company)

    name = "Main Account"
    try:
        Account.remove_account(account_name=name, company=company)
    except Exception:
        pass
    account = Account.get_or_create_account(name=name, company=company,
                                            account_type=account_type)

    currencies = ("GBP", "EUR", "JPY")

    # =======================
    # Add some cashflows to the account
    # =======================
    dates = (ref_date + 30, ref_date + 60, ref_date + 120, ref_date + 240, ref_date + 300, ref_date + 600)
    amounts = (20000., -15000., -25000., 50000., -30000., -20000.)
    for i in range(len(dates)):
        for currency in currencies:
            CashFlow.create_cashflow(account=account,
                                     date=dates[i],
                                     currency=currency,
                                     amount=amounts[i],
                                     status=CashFlow.CashflowStatus.ACTIVE)

    CashFlow.create_cashflow(account=account, date=ref_date + 5,
                             end_date=ref_date + 365,
                             currency="GBP", amount=-12000,
                             periodicity="FREQ=WEEKLY;INTERVAL=1;BYDAY=WE",
                             status=CashFlow.CashflowStatus.ACTIVE)

    CashFlow.create_cashflow(account=account,
                             date=ref_date + 3,
                             end_date=ref_date + 365 * 4,
                             currency="EUR",
                             amount=-2000,
                             periodicity="FREQ=WEEKLY;INTERVAL=1;BYDAY=WE",
                             status=CashFlow.CashflowStatus.ACTIVE)

    # =======================
    # Add hedge settings
    # =======================
    HedgeSettings.create_or_update_settings(account=account,
                                            margin_budget=2.e10,
                                            method="MIN_VAR",
                                            custom={'VolTargetReduction': 0.5})


def create_company_III(account_type):
    from main.apps.hedge.models.hedgesettings import HedgeSettings
    from main.apps.account.models import Company, Account, CashFlow

    ref_date = Date.today()

    # =======================
    # Case III: Company with 3 Accounts, Multi Currency, Mixed Cashflow types in both directions
    # =======================
    company = Company.create_company(name="EOD_Test_3Acct_XCurr", currency="USD")

    if account_type == Account.AccountType.LIVE:
        add_broker_account(company=company)

    num_accounts = 3
    currencies_by_account = [
        ["GBP", "EUR", "JPY", "AUD", "CAD"],
        ["GBP", "EUR", "CAD"],
        ["JPY", "AUD", "CAD"]
    ]
    accounts = []

    for i in range(num_accounts):
        name = f"Account {i + 1}"
        try:
            Account.remove_account(account_name=name, company=company)
        except Exception:
            pass
        account = Account.get_or_create_account(name=name, company=company,
                                                account_type=account_type)
        accounts.append(account)

    # =======================
    # Add some cashflows to the accounts
    # =======================
    reductions = (0.3, 0.4, 0.8)
    periodicities = ["FREQ=WEEKLY;INTERVAL=1;BYDAY=WE", "FREQ=WEEKLY;INTERVAL=2;BYDAY=WE",
                     "FREQ=MONTHLY;INTERVAL=1;BYDAY=WE"]
    amounts = [1000, -2000, 3000]

    for i in range(len(accounts)):
        account = accounts[i]
        for currency in currencies_by_account[i]:
            CashFlow.create_cashflow(account=account,
                                     date=ref_date + 5,
                                     end_date=ref_date + 365 * 5,
                                     currency=currency,
                                     amount=amounts[i],
                                     periodicity=periodicities[i],
                                     status=CashFlow.CashflowStatus.ACTIVE)

        # =======================
        # Add hedge settings
        # =======================
        HedgeSettings.create_or_update_settings(account=account,
                                                margin_budget=2.e10,
                                                method="MIN_VAR",
                                                custom={'VolTargetReduction': reductions[i]})


def run():
    from main.apps.account.models.account import Account
    from hdlib.AppUtils.log_util import get_logger, logging
    logger = get_logger(level=logging.INFO)

    # FUTURE: add cases for the following:
    # 1) A mix of Demo and Draft Accounts
    # 2) Some draft cashflows
    # 3) Cases that hit margin constraints
    # 4) Cases that start off with good margin (due to netting), but hit constraint after cashflow rolloff

    account_type = Account.AccountType.DEMO

    logger.debug("Creating company I")
    create_company_I(account_type=account_type)

    logger.debug("Creating company II")
    create_company_II(account_type=account_type)

    logger.debug("Creating company III")
    create_company_III(account_type=account_type)


if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
