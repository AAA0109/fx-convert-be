import os
import sys

from scripts.lib.only_local import only_allow_local


def run():
    from hdlib.AppUtils.log_util import get_logger, logging
    logger = get_logger(level=logging.INFO)

    from main.apps.hedge.models.hedgesettings import HedgeSettings
    from main.apps.account.models.account import Account
    from main.apps.account.models.cashflow import CashFlow
    from main.apps.account.models.company import Company
    from main.apps.hedge.services.pnl import PnLProviderService
    from main.apps.account.services.cashflow_provider import CashFlowProviderService
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
    from main.apps.hedge.models import CompanyHedgeAction, FxPosition

    from hdlib.DateTime.Date import Date

    ref_date = Date.from_int(20211028)  # just for example, in general dont pass a date for live hedge

    # =======================
    # Add a new company
    # =======================
    company = Company.create_company(name="Demo Company C", currency="USD")

    # =======================
    # Add An Account for that company
    # =======================
    account = Account.get_or_create_account(name="Main Account", company=company)

    # =======================
    # Add some permissible currencies for that account
    # =======================
    if account is None:
        logger.error("Account was None. This is likely because the account failed to be created. Cannot continue.")
        return

    # =======================
    # Add some cashflows to the account
    # =======================
    for date in [20211101, 20211201, 20220201, 20220301, 20220401, 20220501]:
        for currency in ["GBP", "AUD"]:
            CashFlow.create_cashflow(account=account,
                                     date=Date.from_int(date),
                                     currency=currency,
                                     amount=1024.25,
                                     status=CashFlow.CashflowStatus.ACTIVE)

    # =======================
    # Add hedge settings
    # =======================
    settings, _ = HedgeSettings.create_or_update_settings(account=account,
                                                          margin_budget=200,
                                                          method="PERFECT")

    # Get the cash exposures
    exposure = CashFlowProviderService().get_cash_exposures(date=ref_date,
                                                            settings=settings.to_HedgeAccountSettingsHDL())
    print(exposure)

    spot_fx_cash = FxSpotProvider().get_spot_cache(time=ref_date)

    _, company_hedge_action = CompanyHedgeAction.add_company_hedge_action(company=company)
    # Unwind any positions if they exist (if this is your first time running script, they won't)

    # status, unwind_hedge_action = HedgerService().submit_unwind_hedge(account=account,
    #                                                                   company_hedge_action=company_hedge_action)
    # if not status.success():
    #     logger.error(f"Error submitting unwind hedge: {status}")
    # if unwind_hedge_action is not None:
    #     OMSHedgeService().reconcile_company_orders_for_account_type(company_hedge_action=unwind_hedge_action,
    #                                                                 account_type=Account.AccountType.DEMO,
    #                                                                 spot_fx_cache=spot_fx_cash)
    #     logger.info(status)
    # else:
    #     logger.error(f"Error in unwind. Status: {status}")

    # =======================
    # Get the current hedge positions
    # =======================
    positions = FxPosition.get_positions_map_for_accounts(accounts=[account], time=ref_date)[account]
    print(f"Current Hedge Positions for Account:\n{positions}")

    # =======================
    # Check Out what the proposed Hedge should Be
    # =======================
    # status, company_hedge_action = EodAndIntraService(ref_date=ref_date).hedge_company(company=company)
    # logger.info(status)
    # status = OMSHedgeService().reconcile_company_orders_for_account_type(company_hedge_action=company_hedge_action,
    #                                                                      account_type=Account.AccountType.DEMO,
    #                                                                      spot_fx_cache=spot_fx_cash)
    # logger.info(status)
    #
    # positions = FxPosition.get_positions_map_for_accounts(accounts=[account], time=ref_date)[account]
    # print(f"New Hedge Positions for Account:\n{positions}")
    #
    # positions = HedgePositionService().get_aggregate_positions_for_company(time=company_hedge_action.time)
    # print(f"New Hedge Positions for company:\n{positions}")

    # ==================
    # Get the Account Value
    # ==================
    value, currency = PnLProviderService().get_hedge_position_value(account=account)

    print(f"Account value: {value} ({currency})")


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
