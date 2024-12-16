from hdlib.DateTime.Date import Date
from main.apps.hedge.services.eod_and_intra import EodAndIntraService
from scripts.lib.only_local import only_allow_local


def run():
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
    from main.apps.hedge.services.hedge_position import HedgePositionService
    from main.apps.account.models import Company
    from main.apps.hedge.services.account_hedge_request import AccountHedgeRequestService
    from main.apps.hedge.services.oms import OMSHedgeService
    from main.apps.hedge.services.pnl import PnLProviderService
    from main.apps.account.models import Account

    # Just for example, in general don't pass a date for live hedge.
    ref_date = Date.create(year=2021, month=10, day=28, hour=17)
    fx_cache = FxSpotProvider().get_eod_spot_fx_cache(date=ref_date)

    # Get all active companies
    companies = Company.get_companies()
    account_types = (Account.AccountType.DEMO,)

    def print_company_positions():
        # Company's current positions.
        company_positions = HedgePositionService().get_positions_for_company_by_account(company=company, time=ref_date)
        for account, positions in company_positions.items():
            print(f"Account \"{account.name}\":")
            for position in positions:
                print(f"\t{position.fxpair}: {position.amount}")

    for company in companies:
        print(f"\nHedging company: {company.name}")

        print("Initial company positions:")
        print_company_positions()

        # Put in all account hedge requests and OMS order requests for the company.
        status, company_hedge_action = EodAndIntraService(ref_date=ref_date).hedge_company(company=company)

        if status.success():
            if company_hedge_action is None:
                print(f"Success, but company hedge action is none: {status}")
            else:
                print(f"Company hedge action: id={company_hedge_action.id}")
                # Do reconciliation.
                OMSHedgeService().reconcile_company_orders_for_account_type(company_hedge_action=company_hedge_action,
                                                                            account_type=Account.AccountType.DEMO)

                requests_by_account = AccountHedgeRequestService().get_account_hedge_requests(
                    company_hedge_action=company_hedge_action)
                print(f"Made requests for {len(requests_by_account)} accounts for company {company.name}")
                for account, requests in requests_by_account.items():
                    print(f"\tAccount {account}")
                    for request in requests:
                        print(f"\t * {request.account.name}: requested {request.requested_amount} of "
                              f"{request.pair.to_FxPairHDL()}, filled {request.filled_amount}")

            print("Final company positions:")
            print_company_positions()

        else:
            print(f"Status was not success: {status}")

        # Check the Position Value
        position_value, domestic = PnLProviderService().get_hedge_position_value(company=company, date=ref_date,
                                                                                 account_types=account_types)
        print(f"Company Hedge Position Value: {position_value} {domestic}")

        positions_value_by_holding, domestic = PnLProviderService().get_hedge_position_value_by_holding(
            company=company,
            account_types=account_types,
            fx_cache=fx_cache)

        print("Company Hedge Position Values by FxPair:")
        for fxpair, value in positions_value_by_holding.items():
            print(f"\t* {fxpair}: {value} {domestic}")

        # Check the Realized PnL
        realized_pnl = PnLProviderService().get_realized_pnl(end_date=ref_date, company=company,
                                                             account_types=account_types, spot_fx_cache=fx_cache)
        print(f"Realized PnL To Date: {realized_pnl.total_pnl}")

        # Check the UnRealized PnL
        unrealized_pnl = PnLProviderService().get_unrealized_pnl(date=ref_date, company=company,
                                                                 account_types=account_types)

        print(f"UnRealized PnL On Date: {unrealized_pnl.total_pnl}")

    # We are done!
    print("Done with example.")


if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
