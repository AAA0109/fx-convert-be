from typing import List, Tuple, Dict

import numpy as np
import scipy.stats

from hdlib.Core.FxPairInterface import FxPairInterface
from hdlib.Instrument.CashFlow import CashFlows

from hdlib.Hedge.Fx.MinVar.PnLRiskCalculator import PnLRiskCalculator

from hdlib.DateTime.DayCounter import DayCounter_HD
from scipy.stats import norm

from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.HedgeAccount import CashExposures
from hdlib.Universe.Universe import Universe
from hdlib.Utils.PnLCalculator import PnLCalculator
from main.apps.account.models import Account, CashFlow
from main.apps.account.models.parachute_cashflow import ParachuteCashFlow
from main.apps.account.models.parachute_data import ParachuteData
from main.apps.account.services.cashflow_pricer import CashFlowPricerService
from main.apps.account.services.cashflow_provider import CashFlowProviderService
from main.apps.currency.models import Currency, FxPair
from main.apps.events.models import CashflowRolloff, ForwardSettlement
from main.apps.hedge.models import CompanyHedgeAction, HedgeSettings, FxPosition

# Logging.
import logging

from main.apps.hedge.models.fxforwardposition import FxForwardPosition
from main.apps.hedge.models.parachute_record import ParachuteRecordAccount
from main.apps.hedge.models.parachute_spot_positions import ParachuteSpotPositions
from main.apps.oems.models.parachute_forward_configuration import ParachuteForwardConfiguration

logger = logging.getLogger(__name__)


class ParachuteMonth:
    """
    Structure to help with the computation of the hedge for a single parachute month.
    """

    def __init__(self, domestic: Currency, year: int, month: int, parachute_threshold: float):
        # The maximum fraction loss that parachute is configured to allow.
        self._parachute_threshold = parachute_threshold

        # We assume that parachute users (clients) have enough money set aside, or expected to come in from other cashflows,
        # that if parachute succeeds in keeping them above the threshold, they will be able to meet all their obligations.
        # We calculate here the minimum amount of cash that the client's cashflow imply that they must have on hand at the
        # beginning of running parachute.
        self.implied_minimum_client_cash = 0

        self._year = year
        self._month = month

        # Record the domestic currency.
        self._domestic = domestic

        self.forwards: List[FxForwardPosition] = []
        self.cashflows: List[ParachuteCashFlow] = []

        # Spot FX positions attributed to the bucket, per FX pair.
        self._attributed_spot_fx = {}

        # The annualized volatility of the net exposure of the bucket.
        self._ann_volatility = None
        # Net (in domestic) cashflow NPV, valuing rolled off cashflows by their final NPV (spot).
        self._cashflows_npv = None
        # Net (in domestic) cashflow exposure
        self._cashflows_exposure = None
        # Net (in domestic) Fx forward PnL.
        self._forwards_pnl = None

        # Bucket cashflow NPVs by Fx
        self._fx_buckets_cashflows = None
        # Bucket the "amount" of cashflow in each Fx.
        self._fx_bucket_cashflow_amounts = None
        # The exposure in each currency. This does not count value from rolled-off cashflows, which *are* contained
        # in the fx_buckets_cashflow, since they contribute to the value of the bucket, for bookkeeping purposes.
        self._fx_bucket_cashflow_exposure = None

        # Bucket Fx forward PnLs by Fx pair.
        self._fx_buckets_forwards = None
        # Bucket the "amount" of forward in each Fx.
        self._fx_buckets_forward_amounts = None

        # Net cashflow exposures, plus final NPVs (final spot rate, in this case) of rolled-off cashflows, plus forward
        # exposure, plus spot exposure, bucketed by Fx.
        # This can be contrasted with _fx_buckets_net_exposure, which does *not* count the final NPVs of rolled-off
        # cashflows.
        self._fx_buckets_net = None

        # Net cashflow exposure, plus forward exposure, plus spot exposure, per fx-pair.
        # Does not count cashflows that have already rolled off.
        self._fx_buckets_net_exposure = None

        self._initial_npv = None
        self._initial_sum_abs_npv = None

        # Whether to allow forwards to be unwound.
        self._allow_unwind = True

    @property
    def year(self) -> int:
        return self._year

    @property
    def month(self) -> int:
        return self._month

    @property
    def ann_volatility(self):
        return self._ann_volatility

    @property
    def cashflows_npv(self):
        return self._cashflows_npv

    @property
    def cashflows_exposure(self):
        return self._cashflows_exposure

    @property
    def forwards_pnl(self) -> float:
        return self._forwards_pnl

    @property
    def initial_npv(self) -> float:
        return self._initial_npv

    @property
    def npv(self) -> float:
        return self._cashflows_npv + self._forwards_pnl

    @property
    def net_exposure(self) -> float:
        return self._cashflows_exposure + self._forwards_pnl

    @property
    def attributed_spot_fx(self) -> Dict[FxPairInterface, float]:
        return self._attributed_spot_fx

    def get_fx_exposure(self, fx_pair: FxPairInterface) -> float:
        """ Get the net exposure for a specific Fx pair, including the value of rolled-off cashflows. """
        return self._fx_buckets_net_exposure.get(fx_pair, 0.)

    @property
    def initial_sum_abs_npv(self) -> float:
        """ Get the initial sum of the absolute NPVs of the cashflows, in domestic. """
        return self._initial_sum_abs_npv

    def volitility_over(self, days: int) -> float:
        dc = DayCounter_HD()
        return self.ann_volatility * np.sqrt(dc.year_fraction_from_days(days))

    def add_cashflow(self, cashflow: ParachuteCashFlow):
        self.cashflows.append(cashflow)

    def add_forward(self, forward: FxForwardPosition):
        self.forwards.append(forward)

    def add_fx_spot(self, fx_pair: FxPairInterface, amount: float):
        self._attributed_spot_fx.setdefault(fx_pair, 0.)
        self._attributed_spot_fx[fx_pair] += amount

    def get_all_fx_pairs(self):
        """ Get all Fx pairs from any cashflow or forward positions """
        all_fx_pairs = set()
        for fx_pair, _ in self._fx_buckets_net.items():
            all_fx_pairs.add(fx_pair)
        return all_fx_pairs

    def compute(self, universe: Universe):
        self._cashflows_npv = 0.
        self._cashflows_exposure = 0.
        self._forwards_pnl = 0.

        self._fx_buckets_cashflows = {}
        self._fx_buckets_forwards = {}
        self._fx_buckets_net = {}
        self._fx_buckets_net_exposure = {}

        # Bucket all the cashflows and forwards by (month, year).
        self._bucket_month(universe=universe)

        # Get the keys.
        fx_pairs = np.array(list(self._fx_buckets_net_exposure.keys()))
        net_values = np.array(list(self._fx_buckets_net_exposure.values()))

        corrs = universe.fx_universe.fx_corrs.instant_fx_spot_corr_matrix(pairs=fx_pairs).values
        spots = universe.fx_universe.fx_assets.get_fx_spots(pairs=fx_pairs).values
        vols = universe.fx_universe.fx_vols.vols_spots(pairs=fx_pairs).values

        self._validate(fx_pairs, corrs, spots, vols)

        # Calc annual vol.
        risk_calc = PnLRiskCalculator(forwards=spots, vols=vols, correlations=corrs, dt=1.0)
        self._ann_volatility = np.sqrt(risk_calc.variance(net_values / spots))

        self._initial_npv = 0.
        self._initial_sum_abs_npv = 0.
        for cashflow in self.cashflows:
            self._initial_sum_abs_npv += np.abs(cashflow.initial_npv)
            self._initial_npv += cashflow.initial_npv

    def _validate(self, fx_pairs, correlations, spots, vols):
        for i in range(len(fx_pairs) - 1):
            for j in range(i + 1, len(fx_pairs)):
                if np.isnan(correlations[i, j]):
                    raise RuntimeError(f"correlation {fx_pairs[i]} ~ {fx_pairs[j]} is NaN")
        for fx_pair, spot in zip(fx_pairs, spots):
            if np.isnan(spot):
                raise RuntimeError(f"Fx spot rate for {fx_pair} is NaN")
        for fx_pair, spot in zip(fx_pairs, vols):
            if np.isnan(spot):
                raise RuntimeError(f"Fx spot vol for {fx_pair} is NaN")

    def get_fractional_hedge(self, fraction: float) -> Tuple[Dict[FxPairInterface, float], float]:
        """
        Given a hedge fraction in the range [0, 1], return the futures position needed to hedge the remaining exposure
        by that amount.
        """
        logger.debug(f"Getting hedge for fraction {fraction}, allow unwind = {self._allow_unwind}.")

        if fraction <= 0:
            fraction = 0.

        # At most, we fully hedge, or fully unwind.
        if 1. < fraction:
            fraction = 1.
        if fraction < -1.:
            fraction = -1.

        sub_abs_remaining = 0.
        hedge = {}

        if self._allow_unwind:
            # Hedging against the exposures instead of the residual exposures, minus the forwards, allows us to unwind
            # forwards as well as take out new forwards. This is important for the case where we are hedging a bucket
            # where (as will commonly happen, at least in the most general case) not all cashflows roll off on the same
            # pay date. Currently, we target a particular date, the end of the month, for forwards, so we can net. But as
            # cashflows roll off, this actually leaves us directional, via holding the forwards. This is not a problem in
            # and of itself, but we need to carry through with the general parachute logic, and hedge (in this case,
            # by unwinding forwards) when we have too high a probability of breaching.
            for fx, exposure in self._fx_buckets_net_exposure.items():
                hedge[fx] = fraction * exposure
                logger.debug(f"  >> {fx} exposure = {exposure}, hedge = {hedge[fx]}.")
                # This won't mean the exact same thing as in the no-unwinding case, but we do have to return this to
                # keep the logic consistent, and to let the caller known how much hedgeable exposure is remaining.
                sub_abs_remaining += np.abs(exposure)
        else:
            # If not allowed to unwind forwards, we hedge against the residual exposures, i.e. the cashflow exposures
            # minus the forwards. We make sure we never take out a position larger than the residual exposure, and
            # cannot unwind forwards.
            for fx, amount in self._fx_bucket_cashflow_exposure.items():
                current_fwd_amount = self._fx_buckets_forward_amounts.get(fx, 0.)

                # Note that forward amount will be in the opposite direction of the exposure.
                sg = np.sign(amount)
                # Here, we are not allowing forwards positions to be larger than the Fx exposure
                # (but in the opposite direction).
                remainder = sg * np.maximum(0., sg * (amount + current_fwd_amount))

                logger.debug(f"  >> {fx} exposure = {amount}, current fwd amount = {current_fwd_amount}, "
                             f"remainder = {remainder}.")

                sub_abs_remaining += np.abs(remainder)
                hedge[fx] = fraction * remainder

        return hedge, sub_abs_remaining

    def get_fwd_point_data(self, universe: Universe, fx_pair: FxPairInterface):
        last_of_month = Date.create(year=self._year, month=self._month, day=1).last_day_of_month()
        fwd_price = universe.get_forward(fx_pair=fx_pair, date=last_of_month)
        return last_of_month, fwd_price

    def _bucket_month(self, universe: Universe):
        self._bucket_month_cashflows(universe=universe)
        self._bucket_month_forwards(universe=universe)
        # Deal with spot Fx positions.
        self._bucket_spot_fx(universe=universe)

    def _bucket_month_cashflows(self, universe: Universe):
        self._fx_buckets_cashflows = {}
        self._fx_bucket_cashflow_amounts = {}
        self._fx_bucket_cashflow_exposure = {}
        for cashflow in self.cashflows:
            fx_pair = FxPair.get_pair(f"{cashflow.currency}{self._domestic}")

            # Get the value of the cashflow, which may have already rolled off.
            value, has_risk = self._value(cashflow, universe)

            if np.isnan(value):
                raise RuntimeError(f"cannot value cashflow in {cashflow.currency}, pays on {cashflow.pay_date}")

            self._fx_bucket_cashflow_amounts.setdefault(fx_pair, 0.)
            self._fx_bucket_cashflow_amounts[fx_pair] += cashflow.amount

            # If the cashflow has not rolled off, it bears risk.
            if has_risk:
                self._fx_bucket_cashflow_exposure.setdefault(fx_pair, 0.)
                self._fx_bucket_cashflow_exposure[fx_pair] += cashflow.amount

                self._fx_buckets_net_exposure.setdefault(fx_pair, 0.)
                self._fx_buckets_net_exposure[fx_pair] += value

                self._cashflows_exposure += value

                # Compute how much cash the user would have to of had to have on hand at the beginning to cover their
                # obligations for this cashflow, assuming parachute loss threshold holds.
                # Note the negative sign, since the client needs the cash to offset the cashflow.
                self.implied_minimum_client_cash = -(1. - self._parachute_threshold) * cashflow.initial_npv

            self._fx_buckets_cashflows.setdefault(fx_pair, 0.)
            self._fx_buckets_cashflows[fx_pair] += value

            self._fx_buckets_net.setdefault(fx_pair, 0.)
            self._fx_buckets_net[fx_pair] += value

            self._cashflows_npv += value

    def _bucket_month_forwards(self, universe: Universe):
        self._fx_buckets_forwards = {}
        self._fx_buckets_forward_amounts = {}
        for forward in self.forwards:
            fx_pair = forward.fxpair

            self._fx_buckets_forwards.setdefault(fx_pair, 0.)

            current_fwd_rate = self._value_fwd(forward, universe=universe)

            fwd_pnl = forward.amount * (current_fwd_rate - forward.forward_price)
            fwd_pnl = universe.convert_value(value=fwd_pnl, from_currency=fx_pair.quote_currency,
                                             to_currency=self._domestic)

            # Forwards' full values, like cashflows, contribute to the exposure.
            self._fx_buckets_net_exposure.setdefault(fx_pair, 0.)
            self._fx_buckets_net_exposure[fx_pair] += current_fwd_rate * forward.amount

            self._fx_buckets_forward_amounts.setdefault(fx_pair, 0.)
            self._fx_buckets_forward_amounts[fx_pair] += forward.amount

            self._fx_buckets_forwards.setdefault(fx_pair, 0.)
            self._fx_buckets_forwards[fx_pair] += fwd_pnl

            self._fx_buckets_net.setdefault(fx_pair, 0.)
            self._fx_buckets_net[fx_pair] += fwd_pnl

            self._forwards_pnl += fwd_pnl

    def _bucket_spot_fx(self, universe: Universe):
        for fx_pair, amount in self._attributed_spot_fx.items():
            self._fx_buckets_net_exposure.setdefault(fx_pair, 0.)
            self._fx_buckets_net_exposure[fx_pair] += amount

            self._fx_buckets_net.setdefault(fx_pair, 0.)
            self._fx_buckets_net[fx_pair] += amount

    def _value(self, cashflow, universe: Universe) -> Tuple[float, bool]:
        if cashflow.pay_date < universe.ref_date:
            return cashflow.final_npv, False
        return universe.value_cashflow(cashflow, self._domestic), True

    def _value_fwd(self, forward: FxForwardPosition, universe: Universe):
        delivery = Date.from_datetime(forward.delivery_time)
        if delivery < universe.ref_date or (forward.unwind_time and forward.unwind_time <= universe.ref_date):
            return forward.unwind_price
        else:
            return universe.get_forward(fx_pair=forward.fxpair, date=delivery)


def bucket_account_cashflows(hedge_time: Date,
                             account: Account,
                             buckets: Dict[Tuple[int, int], ParachuteMonth]) -> bool:
    # Note that since there is only one account, there will be just one event in the "events" set.
    positions, events = FxPosition.get_positions_for_accounts(time=hedge_time,
                                                              accounts=[account])
    had_spot = 0 < len(positions)

    # Group positions by Fx.
    positions_by_fx = {}
    for position in positions:
        positions_by_fx.setdefault(position.fxpair, []).append(position)

    logger.debug(f"Found {len(positions)} positions for account {account}.")

    # Get all FX from all buckets and positions.
    fx_pairs = set()
    for key, bucket in buckets.items():
        fx_pairs.update(bucket.get_all_fx_pairs())  # All Fx pairs from buckets.
    for fx_pair, positions in positions_by_fx.items():
        fx_pairs.add(fx_pair)  # All Fx pairs from positions.

    # Bucket the positions by month.
    for fx_pair in fx_pairs:
        position = positions_by_fx.get(fx_pair, None)
        # TODO(Nate): There is a bug here - position is a list of positions, not a single position.
        spot_fx_amount = 0. if position is None else position.amount

        # Sum up all the exposures in this currency for all buckets, and track the net positive and negative exposures
        # separately.
        net_fx_exposure, abs_positive_exposure, abs_negative_exposure = 0., 0., 0.
        for key, bucket in buckets.items():
            exposure = bucket.get_fx_exposure(fx_pair)
            net_fx_exposure += exposure
            if 0. < exposure:
                abs_positive_exposure += exposure
            else:
                abs_negative_exposure -= exposure

        # Presumably, the spot position should be smaller in magnitude, and in the opposite direction of the net
        # exposure. If not, we have over-hedged.
        if np.sign(spot_fx_amount) == np.sign(net_fx_exposure):
            logger.warning(
                f"For {fx_pair}, the spot position ({spot_fx_amount}) is in the same direction as the net exposure.")
        if np.abs(spot_fx_amount) > np.abs(net_fx_exposure):
            logger.warning(f"For {fx_pair}, the spot position ({spot_fx_amount}) is larger than the net exposure.")

        # True net exposure: net exposure from cashflows and forwards PLUS exposure from spot.
        total_exposure = net_fx_exposure + spot_fx_amount
        logger.debug(
            f"Total exposure for {fx_pair} is {total_exposure} (cashflow + forward exposure {net_fx_exposure}, "
            f"spot exposure {spot_fx_amount}).")

        # Rule for allocating spot positions:
        # - If the net exposure is 0, we don't need to do anything.
        # - If your exposure is in the opposite direction of the spot exposure, you get perfectly spot hedged (since
        #       there will always be enough exposure in the opposite direction from other buckets to offset you)
        # - If your exposure is in the same direction as the net exposure, the fraction of your exposure that you will
        #       *not* get hedged is proportional to the ratio of your exposure to the total exposure in the same
        #       direction.

        # Allocate the spot position to each bucket, in proportion to the net exposure.
        net_spot_position = 0.
        for key, bucket in buckets.items():
            # For type hinting.
            bucket: ParachuteMonth
            exposure = bucket.get_fx_exposure(fx_pair)

            # If the net exposure is 0, we don't need to do anything.
            if exposure == 0:
                continue

            # If your exposure is in the same direction of the net exposure, you get perfectly spot hedged (since
            # there will always be enough exposure in the opposite direction from other buckets to offset you)
            if np.sign(spot_fx_amount) == np.sign(net_fx_exposure):
                net_spot_position -= exposure
                bucket.add_fx_spot(fx_pair=fx_pair, amount=-exposure)
            # If your exposure is in the same direction as the spot exposure, the fraction of your exposure that you
            # will *not* get hedged is proportional to the ratio of your exposure to the total exposure in the same
            # direction.
            else:
                fraction = exposure / abs_positive_exposure if 0. < exposure else exposure / abs_negative_exposure
                bucket_fx_amount = exposure + fraction * total_exposure
                net_spot_position -= bucket_fx_amount
                bucket.add_fx_spot(fx_pair=fx_pair, amount=-bucket_fx_amount)

        logger.debug(
            f"Net spot position for {fx_pair} is {net_spot_position}, compared to the expected {spot_fx_amount}.")
    # There were spot positions.
    return had_spot


def hedge_parachute_account(account: Account, hedge_time: Date, company_hedge_action: CompanyHedgeAction,
                            universe: Universe, currency: Currency):
    # Get the parachute account data.
    data = ParachuteData.get_for_account(account)
    if not data:
        logger.error(f"Could not find parachute data for account {account}. Cannot do parachute hedge.")
        return
    lower_limit = data.lower_limit

    company_config = ParachuteForwardConfiguration.create_company_parachute_forward_configuration(
        company=account.company)

    # Get all cashflows for the parachute account, bucket by month.
    start_time = hedge_time.first_day_of_month()
    cashflows = ParachuteCashFlow.get_account_cashflows(ref_date=hedge_time, account=account, include_rolled_off=True,
                                                        start_pay_date=start_time)
    buckets = {}
    for cashflow in cashflows:
        key = (cashflow.pay_date.year, cashflow.pay_date.month)
        buckets.setdefault(key, ParachuteMonth(domestic=currency, year=key[0], month=key[1],
                                               parachute_threshold=lower_limit)).add_cashflow(cashflow)

    # Get all forwards for the parachute account, bucket by month.
    forwards = FxForwardPosition.get_forwards_for_account(current_time=hedge_time, account=account)
    logger.debug(f"Found {len(forwards)} forwards for account {account}.")
    for forward in forwards:
        key = (forward.delivery_time.year, forward.delivery_time.month)
        buckets.setdefault(key, ParachuteMonth(domestic=currency, year=key[0], month=key[1],
                                               parachute_threshold=lower_limit)).add_forward(forward)

    try:
        for key, bucket in buckets.items():
            bucket.compute(universe=universe)
    except Exception as ex:
        logger.error(f"Could not compute buckets, cannot do parachute hedge. Error: {ex}")
        return

    # NOTE(Nate): For now, we are hard-coding-off having spot work with parachute accounts.
    handle_fx_spot = False
    if handle_fx_spot:
        # In cases like hard limits, there may be spot positions. We don't want to over-hedge, so we need to assign spot
        # positions to each bucket, and hedge in the presence of the buckets.
        had_spot = bucket_account_cashflows(account=account, hedge_time=hedge_time, buckets=buckets)
        if had_spot:
            # The buckets now contain their spot positions.
            # Recompute buckets.
            try:
                for key, bucket in buckets.items():
                    bucket.compute(universe=universe)
            except Exception as ex:
                logger.error(f"Could not compute buckets, cannot do parachute hedge. Error: {ex}")
                return

    # Find all positions from last time. Collect all Fx pairs for positions that were not set to 0. These are the
    # Fx pairs for which we need to create a ParachuteSpotPosition with amount 0 if they do not have an amount.
    last_spot_positions = ParachuteSpotPositions.get_all_last_records(parachute_account=account, time=hedge_time)
    fx_to_handle = set()
    for spot_position in last_spot_positions:
        if spot_position.amount != 0:
            fx_to_handle.add(spot_position.fxpair)

    # Treat each bucket entirely independently.
    for key, bucket in buckets.items():
        # For type hinting.
        bucket: ParachuteMonth

        # =======================================================================
        #   Attribute spot positions.
        # =======================================================================

        integer_key = key[0] * 100 + key[1]

        # Find the last parachute record for this bucket.
        last_record = ParachuteRecordAccount.get_last_record(parachute_account=account, bucket=integer_key,
                                                             time=hedge_time)
        # Create parachute spot positions.
        realized_pnl, unrealized_pnl = 0., 0.
        bucket_spot_fxpairs = set()
        for fx_pair, amount in bucket.attributed_spot_fx.items():
            bucket_spot_fxpairs.add(fx_pair)
            bucket_realized_pnl, bucket_unrealized_pnl = _set_position(fx_pair=fx_pair,
                                                                       amount=amount,
                                                                       account=account,
                                                                       hedge_time=hedge_time,
                                                                       company_hedge_action=company_hedge_action,
                                                                       universe=universe,
                                                                       currency=currency,
                                                                       key=key)
            realized_pnl += bucket_realized_pnl
            unrealized_pnl += bucket_unrealized_pnl

        # Set zero spot positions for all pairs that were not explicitly listed above, but are in the fx_to_handle set.
        # We do this to show that the position closed.
        for fx_pair in fx_to_handle - bucket_spot_fxpairs:
            # Close the position.
            logger.debug(f"Closing the position for bucket {integer_key}, fx pair {fx_pair}, since the Fx spot "
                        f"attributed is now zero.")
            bucket_realized_pnl, bucket_unrealized_pnl = _set_position(fx_pair=fx_pair,
                                                                       amount=0.,
                                                                       account=account,
                                                                       hedge_time=hedge_time,
                                                                       company_hedge_action=company_hedge_action,
                                                                       universe=universe,
                                                                       currency=currency,
                                                                       key=key)
            realized_pnl += bucket_realized_pnl
            unrealized_pnl += bucket_unrealized_pnl

        # Update PnLs in the new parachute record.
        last_realized_pnl = last_record.realized_pnl if last_record else 0.
        logger.debug(f"For bucket {key}, last realized PnL was {last_realized_pnl}, realized PnL from this adjustment "
                     f"is {realized_pnl}.")
        logger.debug(f"Unrealized PnL for bucket {key} is {unrealized_pnl}.")

        # =======================================================================
        #   Take out forward positions.
        # =======================================================================

        # NOTE(Nate): Using data.lower_limit as a fraction here.
        deviation_limit = bucket.initial_sum_abs_npv * data.lower_limit
        lower_limit = bucket.initial_npv - deviation_limit

        # Determine the max PnL.
        account_pnl = 0
        if last_record is not None:
            account_pnl = bucket.npv - last_record.bucket_npv + last_record.account_pnl
            logger.debug(f"Bucket PnL for bucket ({bucket.year}, {bucket.month}) is {account_pnl}.")

        max_pnl = last_record.max_pnl if last_record else 0.
        max_pnl = np.maximum(max_pnl, account_pnl)

        # If using floating strike parachute, adjust the lower limit, keeping some of the PnL safe.
        adjusted_limit_value = lower_limit
        if 0. < data.floating_pnl_fraction:
            adjusted_limit_value += max_pnl * data.floating_pnl_fraction
            logger.debug(
                f"Adjusting lower limit for bucket ({bucket.year}, {bucket.month}) to capture PnL. Max PnL is "
                f"{max_pnl}, fraction is {data.floating_pnl_fraction}. Adjusted limit value is {adjusted_limit_value}.")

        # Create a record for the month
        record = ParachuteRecordAccount.create_record(parachute_account=account,
                                                      bucket=key,  # Buckets are identified by this integer key.
                                                      company_hedge_action=company_hedge_action,
                                                      bucket_npv=bucket.npv,
                                                      limit_value=lower_limit,
                                                      adjusted_limit_value=adjusted_limit_value,
                                                      p_limit=data.lower_p)
        record.implied_minimum_client_cash = bucket.implied_minimum_client_cash
        # Get the interest that will be earned over the next one day.
        one_day_rate = 1. / universe.get_discount(asset=currency, date=hedge_time + 1) - 1.
        record.forward_client_cash_one_day_pnl = one_day_rate * bucket.implied_minimum_client_cash
        logger.debug(f"Implied minimum client cash is {bucket.implied_minimum_client_cash}, "
                    f"one day rate is {one_day_rate}.")
        logger.debug(f"Forward client cash one day PnL is {record.forward_client_cash_one_day_pnl}.")

        if last_record:
            # Get the number of days since the last record.
            days = (hedge_time - last_record.time).days
            one_day_pnl = days * last_record.forward_client_cash_one_day_pnl
            record.client_implied_cash_pnl = last_record.client_implied_cash_pnl + one_day_pnl
            logger.debug(
                f"Client cash cumulative PnL for bucket ({bucket.year}, {bucket.month}) is "
                f"{record.client_implied_cash_pnl}, one day PnL was {one_day_pnl}.")

        record.realized_pnl = realized_pnl + last_realized_pnl
        record.unrealized_pnl = unrealized_pnl
        record.account_pnl = account_pnl

        time_horizon = 1  # Time horizon in days
        volatility = bucket.volitility_over(days=time_horizon)
        pnl_adjusted_lower_limit = adjusted_limit_value - record.client_implied_cash_pnl
        fraction, p = calculate_reduction(bucket.npv,
                                          lower_limit=pnl_adjusted_lower_limit,
                                          volatility=volatility,
                                          currency=currency,
                                          data=data)
        logger.debug(f"Fractional reduction needed for bucket ({bucket.year}, {bucket.month}) is {fraction}, p = {p}.")

        # If locking, the first time (and any time) we need to hedge, we fully hedge.
        if fraction != 0 and data.lock_lower_limit:
            logger.debug(f"Locking lower limit for bucket ({bucket.year}, {bucket.month}).")
            fraction = 1.

        # Calculate the necessary hedge (maybe none) and the sum of the absolute remaining exposures in each currency.
        needed_hedge, sum_abs_remaining = bucket.get_fractional_hedge(fraction)

        if sum_abs_remaining == 0:
            pass

        # Fill in some data.
        record.cashflows_npv = bucket.cashflows_npv
        record.forwards_pnl = bucket.forwards_pnl
        record.ann_volatility = bucket.ann_volatility
        record.volatility = volatility
        record.p_no_breach = p
        record.time_horizon = time_horizon
        record.fraction_to_hedge = fraction
        record.sum_abs_remaining = sum_abs_remaining
        record.max_pnl = max(last_record.max_pnl, account_pnl) if last_record else 0.
        record.save()

        if 0. < fraction:
            for fx_pair, amount in needed_hedge.items():
                if amount != 0:
                    # The amount is the amount *in domestic* of the hedge. We have to convert it to the base currency.
                    fwd_amount = universe.convert_value(value=amount, from_currency=currency,
                                                        to_currency=fx_pair.get_base_currency())

                    representative_time, fwd_price = bucket.get_fwd_point_data(universe, fx_pair=fx_pair)

                    # Round or otherwise normalize the order size.
                    config = company_config.get_data_for_fxpair(fxpair=fx_pair)

                    if config is None:
                        # TODO: Decide what config = None means, e.g. it could mean "you are not allowed to trade this pair."
                        #   This is what I intend it to mean, that way you can control which forwards a company can trade.
                        logger.warning(
                            f"No forward configuration for {fx_pair}, not trading (requested order size was {fwd_amount}).")
                        continue
                    else:
                        min_amount, do_multiples = config
                        if do_multiples:
                            # Round towards zero.
                            normalized_amount = np.fix(fwd_amount / 1000) * 1000
                        else:
                            normalized_amount = 0. if np.abs(fwd_amount) < min_amount else fwd_amount
                    logger.debug(f"Raw forward amount was {fwd_amount}, normalized amount was {normalized_amount}.")

                    if normalized_amount != 0:
                        # TODO: Use forward order service.
                        forward = FxForwardPosition.add_forward_to_account(account=account,
                                                                           fxpair=fx_pair,
                                                                           enter_time=hedge_time,
                                                                           delivery_time=representative_time,
                                                                           amount=-normalized_amount,
                                                                           forward_price=fwd_price,
                                                                           spot_price=universe.get_spot(
                                                                               fx_pair=fx_pair))
                        logger.debug(
                            f"  >> Taking out a {forward.fxpair} forward for {forward.amount} at price "
                            f"{forward.forward_price}")
                    else:
                        logger.debug(
                            f"  >> Not taking out a forward for {fx_pair} since the rounded amount is too small.")

        record.save()


def _set_position(fx_pair, amount, account: Account, hedge_time: Date, company_hedge_action: CompanyHedgeAction,
                  universe: Universe, currency: Currency, key: Tuple[int, int]):
    integer_key = key[0] * 100 + key[1]
    # Get the last spot position for this bucket.
    last_position = ParachuteSpotPositions.get_last_record(parachute_account=account,
                                                           fxpair=fx_pair,
                                                           bucket=integer_key,
                                                           time=hedge_time)
    if last_position:
        last_amount = last_position.amount
        last_total_price = last_position.total_price
    else:
        last_amount = 0.
        last_total_price = 0.

    last_avg_price = last_total_price / np.abs(last_amount) if last_amount != 0 else 0.
    spot_rate = universe.get_spot(fx_pair=fx_pair)
    new_total_price = PnLCalculator.calc_total_price(old_amount=last_amount,
                                                     new_amount=amount,
                                                     old_price_avg=last_avg_price,
                                                     new_price_avg=spot_rate)
    bucket_realized_pnl = PnLCalculator.calc_realized_pnl(old_amount=last_amount,
                                                          new_amount=amount,
                                                          old_price_avg=last_avg_price,
                                                          # New price at which position was obtained, i.e. spot rate.
                                                          new_price_avg=spot_rate)
    # Make sure PnL is in domestic.
    bucket_realized_pnl = universe.convert_value(value=bucket_realized_pnl,
                                                 from_currency=fx_pair.get_base_currency(),
                                                 to_currency=currency)
    realized_pnl = bucket_realized_pnl

    logger.debug(f"Creating parachute spot position for bucket {integer_key}, fx pair {fx_pair}, amount "
                f"{amount}.")
    spot_position = ParachuteSpotPositions.create_record(bucket=key,
                                                         parachute_account=account,
                                                         company_hedge_action=company_hedge_action,
                                                         fxpair=fx_pair,
                                                         amount=amount,
                                                         total_price=new_total_price)
    unrealized, pnl_currency = spot_position.unrealized_pnl(current_rate=spot_rate)
    unrealized_pnl = universe.convert_value(value=unrealized, from_currency=pnl_currency,
                                            to_currency=currency)

    return realized_pnl, unrealized_pnl


def calculate_reduction(account_value: float, lower_limit: float, volatility: float, currency: Currency,
                        data: ParachuteData) -> Tuple[float, float]:
    """
    Calculate the fraction reduction in exposure needed to reduce probability of breach to the correct level, returns
    this fraction, and the (pre-hedge) probability of not breaching.
    """
    distance = account_value - lower_limit
    num_sigmas = np.maximum(0., distance / volatility)
    logger.debug(f"The buffer between the account value and lower limit is {distance:.3f}, the daily volatility is "
                f"{volatility:.3f} {currency}. This is {num_sigmas:.3f} 'sigmas' away.")
    if distance <= 0:
        # We must fully hedge, probability of not breaching is 0.
        return 1.0, 0.0

    else:  # Note that distance > 0
        # Check if we need to increase the hedge. Calculate the probability of *not* breaching.
        p = norm.cdf(num_sigmas)
        logger.debug(f"The probability that the buffer is not breached over the next day is {p}.")

        if p < data.lower_p:
            # Hedge to get back to data.upper_p.
            logger.debug(f"Probability of not exceeding the limit in the next day is only {p}, which is lower than "
                        f"the bound {data.lower_p}. Adding hedge, target is {data.upper_p}.")

            # Note: PPF = Point Percentile Function.
            target_vol = distance / scipy.stats.norm.ppf(data.upper_p)

            vol_reduction = 1. - target_vol / volatility
            logger.debug(f"Need a volatility reduction of {vol_reduction}.")

            return vol_reduction, p
        # No reduction needed.
        return 0., p


def hedge_parachute(hedge_time: Date, company_hedge_action: CompanyHedgeAction, universe: Universe):
    logger.debug(f"Running hedges for parachute accounts.")

    company = company_hedge_action.company
    currency = company.currency

    parachute_strategy_types: Tuple[Account.AccountStrategy] = (Account.AccountStrategy.PARACHUTE,
                                                                Account.AccountStrategy.HARD_LIMITS)
    parachute_accounts = Account.get_account_objs(company=company,
                                                  strategy_types=parachute_strategy_types,
                                                  exclude_hidden=True)
    logger.debug(f"Found {len(parachute_accounts)} parachute accounts for company {company}.")
    if len(parachute_accounts) == 0:
        logger.debug(f"No parachute accounts for company {company}.")
        return

    for account in parachute_accounts:
        logger.debug(f"Hedging parachute account {account}.")
        hedge_parachute_account(account=account, hedge_time=hedge_time, company_hedge_action=company_hedge_action,
                                universe=universe, currency=currency)
