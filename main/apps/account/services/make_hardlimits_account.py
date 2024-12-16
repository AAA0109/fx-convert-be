from hdlib import DateTime
from main.apps.account.models import Account, CashFlow, get_hdl_cashflows, iter_active_cashflows, HardLimitsAccountData
from main.apps.currency.models import Currency
from main.apps.marketdata.services.universe_provider import UniverseProviderService


def create_forward_limit_order(rate: float,
                               account: Account,
                               max_date: DateTime,
                               base_amount: float,
                               base_currency: Currency,
                               quote_currency: Currency):
    """ Create a forward limit order for the given account. """
    pass


def make_account_hard_limits_account(ref_date: DateTime, configuration: HardLimitsAccountData):
    account = configuration.account
    quote_currency = account.company.currency

    # Find all cashflows for the account and place limit orders for all of them.
    cashflows = CashFlow.objects.filter(account=account)

    # Create the current universe.
    universe_provider = UniverseProviderService()
    universe = universe_provider.make_universe(currencies={quote_currency},
                                               ref_date=ref_date,
                                               create_corr=False,
                                               create_vols=False,
                                               bypass_errors=True)

    for cf in cashflows:
        generator = iter_active_cashflows(cfs=cf, ref_date=ref_date, include_cashflows_on_vd=True, include_end=True,
                                          max_date_in_future=ref_date + 365 * 5)
        for true_cashflow in generator:
            pay_date = true_cashflow.pay_date
            amount = true_cashflow.amount
            currency = true_cashflow.currency

            # Find the current rate
            rate = universe.convert_value(value=1, from_currency=currency, to_currency=quote_currency)

            # Create the lower limit order.
            # If the cashflow amount is positive, that means we are receiving the cashflow, so we lose money if the
            # rate goes down, so we sell a forward at the lowest rate we are willing to accept.
            # If the cashflow amount is negative, that means we are paying the cashflow, so we lose money if the rate
            # goes up, so we buy a forward at the highest rate we are willing to accept.
            #
            # We want to ensure that the *amount* of cash is at least some amount, so we do not per-say care about the
            # NPV of the cashflow, but about locking in the spot rate (this is the assumption).
            lower_rate = configuration.lower_limit_fraction * rate if 0 < amount \
                else rate / configuration.lower_limit_fraction
            create_forward_limit_order(rate=lower_rate, account=account, max_date=pay_date, base_amount=-amount,
                                       base_currency=currency, quote_currency=quote_currency)

            # Potentially, create the upper limit order.
            # We do this to take a profit at a certain level.
            if configuration.upper_limit_fraction is not None:
                upper_rate = configuration.upper_limit_fraction * rate if 0 < amount \
                    else rate / configuration.upper_limit_fraction
                create_forward_limit_order(rate=upper_rate, account=account, max_date=pay_date, base_amount=amount,
                                           base_currency=currency, quote_currency=quote_currency)
