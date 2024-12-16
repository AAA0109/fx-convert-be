import abc
import logging
from abc import ABCMeta, abstractmethod
from typing import Dict, Iterable, List, Tuple, Optional

from hdlib.Hedge.Fx.Util.PositionChange import PositionChange
from hdlib.Core.FxPair import FxPair as FxPairHDL, FxPair
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Cash.CashPositions import VirtualFxPosition, CashPositions
from hdlib.Hedge.Fx.Util.FxPnLCalculator import FxPnLCalculator
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache
from hdlib.Utils import PnLCalculator

from main.apps.account.models import Company, Account
from main.apps.broker.models import Broker
from main.apps.account.services.cashflow_provider import CashFlowProviderInterface, CashFlowProviderService
from main.apps.currency.models import Currency
from main.apps.hedge.models import FxPosition
from main.apps.hedge.services.hedge_position import HedgePositionService
from main.apps.margin.models.margin import FxSpotMargin, MarginDetail
from main.apps.margin.services.DepositService import DepositService
from main.apps.margin.services.broker_margin_service import BrokerMarginServiceInterface, DbBrokerMarginService
from main.apps.margin.services.calculators import MarginRatesCache, MarginCalculator
from main.apps.margin.services.calculators.ibkr import IBMarginCalculator
from main.apps.margin.services.margin_detail_service import MarginDetailServiceInterface, DbMarginDetailService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

logger = logging.getLogger(__name__)

class ProjectedMargin:
    def __init__(self, date: Date, amount_before_deposit: float, amount_after_deposit: float, excess: float,
                 total_hedge: float, positions: List[VirtualFxPosition]):
        self.date = date
        self.amount_before_deposit = amount_before_deposit
        self.amount_after_deposit = amount_after_deposit
        self.excess = excess
        self.total_hedge = total_hedge
        self.positions = positions

    def __eq__(self, other):
        return self.date == other.date and \
            self.amount_before_deposit == other.amount_before_deposit and \
            self.amount_after_deposit == other.amount_after_deposit and \
            self.excess == other.excess and \
            self.total_hedge == other.total_hedge and \
            self.positions == other.positions

    def __str__(self):
        return f"ProjectedMargin(date={self.date}, amount_before_deposit={self.amount_before_deposit}, " \
               f"amount_after_deposit={self.amount_after_deposit}, excess={self.excess}, total_hedge={self.total_hedge}, " \
               f"positions={self.positions})"

    def __repr__(self):
        return self.__str__()

    def health_score(self, multiplier=2.0):
        if self.amount_before_deposit == 0:
            return 1.0

        return self.excess / self.amount_before_deposit / multiplier

    def health_score_after_deposit(self, multiplier=2.0):
        if self.amount_after_deposit == 0:
            return 1.0

        return self.excess / self.amount_after_deposit / multiplier

    @property
    def cash_positions(self):
        cash_positions = CashPositions()
        # Add cash from virtual Fx positions.
        for v_fx in self.positions:
            cash_positions.add_cash_from_virtual_fx(v_fx)
        return cash_positions


class MarginHealthReport:
    def __init__(self,
                 margin_detail: MarginDetail,
                 minimum_deposit_or_withdrawl: float,
                 recommended_deposit_or_withdrawl: float,
                 baseline_margin: List[ProjectedMargin],
                 projected_margins_pending: List[ProjectedMargin],
                 projected_margins_theoretical: List[ProjectedMargin]):
        self.margin_detail = margin_detail
        self.recommended_deposit_or_withdrawl = recommended_deposit_or_withdrawl
        self.minimum_deposit_or_withdrawl = minimum_deposit_or_withdrawl
        self.baseline_margin = baseline_margin
        self.projected_margins_pending = projected_margins_pending
        self.projected_margins_theoretical = projected_margins_theoretical

    @property
    def recommended_deposit(self):
        if self.recommended_deposit_or_withdrawl > 0:
            return self.recommended_deposit_or_withdrawl
        else:
            return 0

    @property
    def recommended_withdrawl(self):
        if self.recommended_deposit_or_withdrawl < 0:
            return self.recommended_deposit_or_withdrawl
        else:
            return 0

    @property
    def minimum_deposit(self):
        if self.minimum_deposit_or_withdrawl > 0:
            return self.minimum_deposit_or_withdrawl
        else:
            return 0

    @property
    def maximum_withdrawl(self):
        if self.minimum_deposit_or_withdrawl < 0:
            return self.minimum_deposit_or_withdrawl
        else:
            return 0

    def worst_projected_margin(self):
        if not self.projected_margins_pending:
            return None
        return min(self.projected_margins_pending, key=lambda m: m.health_score())

    def best_projected_margin(self):
        if not self.projected_margins_pending:
            return None
        return max(self.projected_margins_pending, key=lambda m: m.health_score())
class MarginRatesCacheProvider(abc.ABC):
    @abc.abstractmethod
    def get_margin_rates_cache(self, broker: Broker) -> MarginRatesCache:
        raise NotImplementedError()


class DBMarginRatesCashProvider(MarginRatesCacheProvider):

    def get_margin_rates_cache(self, broker: Broker) -> MarginRatesCache:
        """
        NOTE(Nate): For now, we only store the current margin rates, and therefore do not have a concept of
        there being "historical margin."
        """
        cache = MarginRatesCache(broker=broker)
        for margin_detail in FxSpotMargin.objects.filter(broker=broker).prefetch_related().select_related():
            fx_pair = margin_detail.pair
            cache.margin[(fx_pair.base_currency.mnemonic, fx_pair.quote_currency.mnemonic)] = margin_detail
        return cache


class MarginProviderServiceInterface(IBMarginCalculator, metaclass=ABCMeta):
    @abstractmethod
    def get_margin_detail(self,
                          company: Company,
                          date: Date,
                          account_type: Account.AccountType = Account.AccountType.LIVE) -> Optional[MarginDetail]:
        pass

    @abstractmethod
    def compute_projected_margin(self, date, company, account_type, additional_cash, days_to_project):
        """
        Compute a projection of how much margin will be required over some time frame.

        A right continuous representation of the projected margin is returned, i.e. [date1, date2, ...], [m1, m2,...]
        means that starting on date1, and going up to (not including) date2, the margin is m1, starting on date2 and
        going up to (not including) date3, the margin is m2, etc. The last pillar represents the margin up until
        date + days_to_project.
        """
        pass

    @abstractmethod
    def get_recommended_and_minimum_deposit(self,
                                            company: Company,
                                            date: Date,
                                            account_type: Account.AccountType,
                                            additional_cash: Optional[Dict[Currency, float]] = None,
                                            days_to_project: int = 30) -> Tuple[float, float]:
        pass

    @abstractmethod
    def compute_margin_for_position(self,
                                    old_new_positions: PositionChange,
                                    company: Company,
                                    date: Date,
                                    account_type: Account.AccountType = Account.AccountType.LIVE,
                                    spot_fx_cache: Optional[SpotFxCache] = None) -> Optional[MarginDetail]:
        pass

    @abstractmethod
    def get_margin_health_report(self, company: Company, custom_amount=None) -> Optional[MarginHealthReport]:
        pass


class MarginProviderService(MarginProviderServiceInterface):
    """
    Service responsible for providing margin details and change in margin (what-if) calculations
    """

    def __init__(self,
                 margin_calculator: MarginCalculator,
                 broker_service: BrokerMarginServiceInterface,
                 margin_rates_cache_provider: MarginRatesCacheProvider,
                 cash_provider_service: CashFlowProviderInterface,
                 fx_spot_provider: FxSpotProvider,
                 hedge_position_service: HedgePositionService,
                 margin_detail_service: MarginDetailServiceInterface,
                 pnl_calculator: PnLCalculator,
                 deposit_service: DepositService,
                 margin_multiplier=2.0):
        super().__init__()
        self._multiplier = margin_multiplier
        self._margin_calculator = margin_calculator
        self._broker_service = broker_service
        self._margin_rates_cache_provider = margin_rates_cache_provider
        self._cash_provider_service = cash_provider_service
        self._fx_spot_provider = fx_spot_provider
        self._hedge_position_service = hedge_position_service
        self._margin_detail_service = margin_detail_service
        self._pnl_calculator = pnl_calculator
        self._deposit_service = deposit_service

    def get_margin_detail(self, company: Company, date: Date,
                          account_type: Account.AccountType = Account.AccountType.LIVE) -> Optional[MarginDetail]:
        logger.debug(f"  ** Getting margin detail for company %s on date %s", company, date)
        broker_account = self._broker_service.get_broker_for_company(company=company, account_type=account_type)
        if not broker_account:
            logger.warning(f"  ** No broker account found for company %s", company)
            return MarginDetail(company=company,
                                date=date,
                                margin_requirement=0,
                                excess_liquidity=0)
        broker = broker_account.broker
        if not company.has_live_accounts(acct_types=[account_type.value]):
            logger.debug(f"  ** Company %s does not have any live accounts", company)
            return MarginDetail(company=company,
                                date=date,
                                margin_requirement=0,
                                excess_liquidity=0)
        logger.debug(f"  ** Getting cash positions for company %s on date %s", company, date)
        cp, _ = self._hedge_position_service.get_cash_positions(company=company, date=date)
        logger.debug(f"  ** Got %d cash positions for company %s on date %s", len(cp.cash_by_currency), company, date)

        logger.debug(f"  ** Getting broker margin summary for company %s on date %s", company, date)
        summary = self._broker_service.get_broker_margin_summary(company=company,
                                                                 account_type=account_type)
        logger.debug(f"  ** Got broker margin summary for company %s on date %s", company, date)

        if cp.empty:
            logger.debug(f"  ** No cash positions for company %s on date %s", company, date)
            return MarginDetail(company=company,
                                date=date,
                                margin_requirement=summary.maint_margin,
                                excess_liquidity=summary.excess_liquidity)
        cp.add_cash(company.currency, summary.additional_cash)

        logger.debug(f"  ** Getting spot fx rates on date %s", date)
        spot_fx_cache = self._fx_spot_provider.get_spot_cache(time=date)

        logger.debug(f"  ** Getting margin rates cache for broker %s", broker)
        margin_rates = self._margin_rates_cache_provider.get_margin_rates_cache(broker=broker)
        logger.debug(f"  ** Computing margin requirement for company %s on date %s", company, date)
        margin = self._margin_calculator.compute_margin(cash_positions=cp,
                                                        domestic=company.currency,
                                                        spot_fx_cache=spot_fx_cache,
                                                        margin_rates=margin_rates,
                                                        multiplier=self._multiplier)
        logger.debug(f"  ** Computed margin requirement for company %s on date %s", company, date)
        return MarginDetail(company=company,
                            date=date,
                            margin_requirement=margin,
                            excess_liquidity=summary.equity_with_loan_value - margin)

    @staticmethod
    def create_margin_rates_cache(broker: Broker) -> MarginRatesCache:
        """
        NOTE(Nate): For now, we only store the current margin rates, and therefore do not have a concept of
        there being "historical margin."
        """
        cache = MarginRatesCache(broker=broker)
        for margin_detail in FxSpotMargin.objects.filter(broker=broker):
            fx_pair = margin_detail.pair
            cache.margin[fx_pair] = margin_detail
        return cache

    def compute_projected_margin(self,
                                 date: Date,
                                 company: Company,
                                 account_type: Account.AccountType = Account.AccountType.LIVE,
                                 additional_cash=None,
                                 days_to_project: int = 30) -> List[ProjectedMargin]:
        """
        Compute a projection of how much margin will be required over some time frame.

        A right continuous representation of the projected margin is returned, i.e. [date1, date2, ...], [m1, m2,...]
        means that starting on date1, and going up to (not including) date2, the margin is m1, starting on date2 and
        going up to (not including) date3, the margin is m2, etc. The last pillar represents the margin up until
        date + days_to_project.
        """
        if additional_cash is None:
            additional_cash = {}

        logger.debug(f"  ** Computing projected margin for company %s on date %s", company, date)
        domestic = company.currency
        broker_account = self._broker_service.get_broker_for_company(company=company, account_type=account_type)
        if not broker_account:
            return []
        if not company.has_live_accounts(acct_types=[account_type.value]):
            return []
        broker = broker_account.broker
        logger.debug(f"  ** Getting broker account summary for company %s on date %s", company, date)
        try:
            summary = self._broker_service.get_broker_margin_summary(company=company,
                                                                 account_type=account_type)
        except Exception as e:
            logger.error(e.with_traceback(e.__traceback__))
            return []
        logger.debug(f"  ** Getting spot fx rates on date %s", date)
        spot_fx_cache = self._fx_spot_provider.get_spot_cache(time=date)

        logger.debug(f"  ** Computing exposure for company %s on date %s", company, date)
        # We need to treat all the accounts of the company, but be aware that the accounts may have different hedge
        # settings.
        all_accounts = company.acct_company.filter(type=account_type).all()
        data_by_account = {}
        all_dates = set({})
        exposures_in_domestic = {}
        for account in all_accounts:
            if not account.has_hedge_settings():
                continue
            end_date = Date.from_datetime_date(date + days_to_project)
            logger.debug(f"  ** Getting projected raw exposure for account %s on date %s", account, date)
            exposures = self._cash_provider_service.get_projected_raw_cash_exposures(account=account,
                                                                                     start_date=date,
                                                                                     end_date=end_date)
            logger.debug(f"  ** Converting exposure to domestic currency for account %s on date %s", account, date)
            for d, exposure in exposures:
                for currency, amount in exposure:
                    if currency == domestic:
                        exposures_in_domestic[d] = exposures_in_domestic.get(date, 0) + abs(amount)
                    else:
                        fx = spot_fx_cache.get_fx(fx_pair=FxPairHDL(currency, domestic))
                        if not fx:
                            raise ValueError("No FX rate found for %s" % FxPairHDL(currency, domestic))
                        exposures_in_domestic[d] = exposures_in_domestic.get(d, 0) + abs(amount) * fx
                all_dates.add(d)
            if len(exposures) > 0:
                data_by_account[account] = exposures
        logger.debug(f"  ** Finished computing exposure for company %s on date %s", company, date)
        # This would happen if there were no cashflows.
        if len(data_by_account) == 0:
            return []
        iter_by_account = {account: 0 for account in all_accounts}

        # Create a universe. We will assume that the universe is the same on ever date.
        logger.debug(f"  ** Getting margin rates cache for broker %s", broker)
        margin_rates = self._margin_rates_cache_provider.get_margin_rates_cache(broker=broker)

        logger.debug(f"  ** Computing projected margin for company %s on date %s for %s dates", company, date, len(all_dates))
        # Compute the margin for each date.
        projected_margins = []
        for it, date in enumerate(sorted(all_dates)):
            # Get the cash exposures for the accounts
            all_positions = []
            for account in all_accounts:
                iter = iter_by_account[account]
                data = data_by_account.get(account, None)
                if not data:
                    continue
                settings = account.hedge_settings
                # Increment counter if necessary.
                if iter < len(data) - 1 and data[iter + 1][0] <= date:
                    iter_by_account[account] += 1
                    iter += 1
                # Get raw cash exposures.
                _, exposures = data[iter]

                # Compute some approximations of what positions the hedge would take.
                # settings.custom_settings

                # TODO: Do this better. First approximation: take some proportional position in each currency.
                target_vol_reduction = settings.custom.get('VolTargetReduction', 1.0) if settings.custom else 1.0
                for currency, amount in exposures:
                    if currency == domestic:
                        continue
                    fxpair = FxPairHDL(base=currency, quote=domestic)
                    amount *= target_vol_reduction  # Proportional position.
                    fx = VirtualFxPosition(fxpair=fxpair, amount=amount, ave_price=spot_fx_cache.get_fx(fxpair))
                    all_positions.append(fx)
            # No positions => no margin.
            if len(all_positions) == 0:
                projected_margins.append(ProjectedMargin(date=date,
                                                         amount_before_deposit=0.0,
                                                         amount_after_deposit=0.0,
                                                         excess=summary.equity_with_loan_value,
                                                         total_hedge=exposures_in_domestic[date],
                                                         positions=[]))
                continue

            logger.debug(f"  ** Computing margin for company %s on date %s from VFX positions", company, date)
            # Compute approximate margin.
            margin_before_additional_cash = self._margin_calculator.compute_margin_from_vfx(
                virtual_fx=all_positions,
                domestic=domestic,
                spot_fx_cache=spot_fx_cache,
                margin_rates=margin_rates,
                additional_cash={domestic: summary.additional_cash})

            excess = summary.additional_cash + additional_cash.get(domestic, 0) - margin_before_additional_cash
            if additional_cash.get(domestic, None):
                margin_after_additional_cash = margin_before_additional_cash
            else:
                additional_cash[domestic] = additional_cash.get(domestic, 0) + summary.additional_cash
                margin_after_additional_cash = self._margin_calculator.compute_margin_from_vfx(
                    virtual_fx=all_positions,
                    domestic=domestic,
                    spot_fx_cache=spot_fx_cache,
                    margin_rates=margin_rates,
                    additional_cash={domestic: additional_cash[domestic]})
            cash_positions = CashPositions()
            # Add cash from virtual Fx positions.
            for v_fx in all_positions:
                cash_positions.add_cash_from_virtual_fx(v_fx)

            projected_margins.append(ProjectedMargin(date=date,
                                                     amount_before_deposit=margin_before_additional_cash,
                                                     amount_after_deposit=margin_after_additional_cash,
                                                     excess=excess,
                                                     total_hedge=exposures_in_domestic[date],
                                                     positions=all_positions))

        return projected_margins

    def _get_virtual_fx_positions(self,
                                  company: Company,
                                  date: Date):
        position_objs = self._get_position_objects(company=company, date=date)
        virtual_fx = []
        for position in position_objs:
            virtual_fx.append(VirtualFxPosition(fxpair=position.fxpair,
                                                amount=position.amount,
                                                ave_price=position.average_price[0]))
        return virtual_fx

    def _get_position_objects(self,
                              company: Company,
                              date: Date) -> Iterable['FxPosition']:
        return FxPosition.get_position_objs(company=company, time=date)[0]

    def get_recommended_and_minimum_deposit(self, company: Company,
                                            date: Date,
                                            account_type: Account.AccountType,
                                            additional_cash: Optional[Dict[Currency, float]] = None,
                                            days_to_project: int = 30) -> Tuple[float, float]:
        if additional_cash is None:
            additional_cash = {}

        projected_margins = self.compute_projected_margin(date=date, company=company, account_type=account_type,
                                                          days_to_project=days_to_project,
                                                          additional_cash=additional_cash)
        projected_margins.sort(key=lambda x: x.health_score())
        if len(projected_margins) == 0:
            return 0.0, 0.0

        positions = projected_margins[0].cash_positions
        logger.debug(f"  ** Getting fx spot rates for {company} on {date}")
        spot_fx_cache = self._fx_spot_provider.get_spot_cache(time=date)
        logger.debug(f"  ** Getting broker account for %s on %s", company, date)
        broker_account = self._broker_service.get_broker_for_company(company=company, account_type=account_type)
        if not broker_account:
            return 0.0, 0.0
        broker = broker_account.broker
        logger.debug(f"  ** Getting margin rates for %s on %s", company, date)
        margin_rates_cache = self._margin_rates_cache_provider.get_margin_rates_cache(broker=broker)
        if projected_margins[0].health_score() >= 0.5:
            logger.debug(f"  ** Margin health is above 0.5 return 0 minimum required deposit")
            minimum_margin = 0.0
        else:
            logger.debug(f"  ** Getting minimum deposit for %s on %s", company, date)
            minimum_margin = self._margin_calculator.compute_required_cash_deposit_or_withdrawl(
                cash_positions=positions,
                domestic=company.currency,
                spot_fx_cache=spot_fx_cache,
                margin_rates=margin_rates_cache,
                target_health=0.5)
            logger.debug(f"  ** Finished computing minimum deposit for %s on %s", company, date)
        logger.debug(f"  ** Getting recommended deposit for %s on %s", company, date)
        recommended_margin = self._margin_calculator.compute_required_cash_deposit_or_withdrawl(
            cash_positions=positions,
            domestic=company.currency,
            spot_fx_cache=spot_fx_cache,
            margin_rates=margin_rates_cache,
            target_health=1.0)
        logger.debug(f"  ** Finished computing recommended deposit for %s on %s", company, date)
        return minimum_margin, recommended_margin

    def compute_margin_for_position(self,
                                    old_new_positions: PositionChange,
                                    company: Company,
                                    date: Date,
                                    account_type: Account.AccountType = Account.AccountType.LIVE,
                                    spot_fx_cache: Optional[SpotFxCache] = None) -> Optional[MarginDetail]:
        if not spot_fx_cache:
            spot_fx_cache = self._fx_spot_provider.get_spot_cache(time=date)
        broker_account = self._broker_service.get_broker_for_company(company=company, account_type=account_type)
        if broker_account is None:
            logger.debug(f"Note that company {company} does not have a broker account. This must be a test.")
            return None

        broker = broker_account.broker
        vfx_positions = []
        new_positions, old_positions = {}, {}
        logger.debug("Aggregating VFX positions for company %s on %s", company, date)
        for fxpair, amount in old_new_positions.new_positions.items():
            fxpair: FxPair = FxPair.from_str(fxpair.name)
            vfx = VirtualFxPosition(fxpair=fxpair, amount=amount, ave_price=spot_fx_cache.get_fx(fxpair))
            vfx_positions.append(vfx)
            new_positions[fxpair] = amount
        logger.debug("Aggregated %d VFX positions for company %s on %s", len(vfx_positions), company, date)

        logger.debug("Getting broker margin summary for company %s on %s", company, date)
        broker_summary = self._broker_service.get_broker_margin_summary(company=company, account_type=account_type)
        broker_additional_cash = broker_summary.additional_cash
        additional_cash = {company.currency: broker_additional_cash}
        logger.debug("Getting cash positions for company %s on %s", company, date)
        _, positions = self._hedge_position_service.get_cash_positions(None, company, date)
        for fxpos in positions:
            old_positions[fxpos.fxpair] = VirtualFxPosition(fxpos.fxpair, fxpos.amount, fxpos.average_price[0])
        if len(new_positions) == 0:
            logger.debug("No new positions for company %s on %s", company, date)
            pnl = 0
        else:
            logger.debug("Calculating P&L for company %s on %s", company, date)
            pnl = self._pnl_calculator.calc_realized_pnl_of_position_change(spot_fx_cache=spot_fx_cache,
                                                                            old_positions=old_positions,
                                                                            new_positions=new_positions,
                                                                            currency=company.currency)
        logger.debug("Done calculating P&L for company %s on %s", company, date)
        additional_cash[company.currency] += pnl

        logger.debug("Computing new margin requirements for company %s on %s", company, date)
        new_margin = self._margin_calculator.compute_margin_from_vfx(
            virtual_fx=vfx_positions,
            domestic=company.currency,
            spot_fx_cache=spot_fx_cache,
            margin_rates=self._margin_rates_cache_provider.get_margin_rates_cache(broker),
            additional_cash=additional_cash)
        logger.debug("Done computing new margin requirements for company %s on %s", company, date)
        return MarginDetail(company=company,
                            date=date,
                            margin_requirement=new_margin,
                            excess_liquidity=broker_summary.equity_with_loan_value - new_margin)


    def get_margin_health_report(self, company: Company, custom_amount=None) -> Optional[MarginHealthReport]:
        date = Date.from_datetime(Date.now())
        if custom_amount:
            pending_cash = {
                company.currency: custom_amount
            }
            logger.debug(f"  * Using custom cash amount: {custom_amount}")
        else:
            pending_cash_amount = self._deposit_service.get_pending_deposits(company=company, date=date)
            pending_cash = {
                company.currency: pending_cash_amount
            }
            logger.debug(f"  * Pending cash amount: {pending_cash_amount}")
        logger.debug(f"  * Getting recommended and minimum deposit")
        minimum_deposit, recommended_deposit = self.get_recommended_and_minimum_deposit(
            company=company,
            date=date,
            account_type=Account.AccountType.LIVE,
            additional_cash=pending_cash)
        logger.debug(f"  * minimum deposit: {minimum_deposit}, recommended deposit: {recommended_deposit}")

        logger.debug(f"  * Additional cash amount used in margin check is pending_cash: "
                    f"{pending_cash[company.currency]}")
        if custom_amount:
            additional_cash = {
                company.currency: custom_amount
            }
            logger.debug(f"  * Additional cash available used in theoretical margin check is set to custom_amount: "
                        f"{additional_cash[company.currency]}")
        else:
            additional_cash = {
                company.currency: recommended_deposit + pending_cash_amount
            }
            logger.debug(f"  * Additional cash amount used in theoretical margin check is "
                        f"pending_cash + recommended_deposit: {additional_cash[company.currency]}")

        logger.debug(f"  * Computing projected margin with only pending_cash={pending_cash}")
        baseline_margin = self.compute_projected_margin(date=date,
                                                        company=company,
                                                        account_type=Account.AccountType.LIVE)

        projected_margins_pending = self.compute_projected_margin(date=date,
                                                                  company=company,
                                                                  account_type=Account.AccountType.LIVE,
                                                                  additional_cash=pending_cash)
        logger.debug(f"  * Margin health score with only pending deposits: "
                    f"{[(margin.date, margin.health_score()) for margin in projected_margins_pending]}")
        logger.debug(f"  * Computing projected margin with pending_cash= + recommended deposit = {additional_cash}")
        projected_margins_theoretical = self.compute_projected_margin(date=date,
                                                                      company=company,
                                                                      account_type=Account.AccountType.LIVE,
                                                                      additional_cash=additional_cash)
        logger.debug(f"  * Margin health score with pending_cash + recommended deposit={additional_cash}: "
                    f"{[(margin.date, margin.health_score()) for margin in projected_margins_theoretical]}")

        logger.debug(f"  * Getting today's actual margin")
        margin_detail = self.get_margin_detail(company=company, date=date, account_type=Account.AccountType.LIVE)
        logger.debug(f"  * Today's margin balance: {margin_detail.excess_liquidity}")
        return MarginHealthReport(margin_detail=margin_detail,
                                  minimum_deposit_or_withdrawl=minimum_deposit,
                                  recommended_deposit_or_withdrawl=recommended_deposit,
                                  baseline_margin=baseline_margin,
                                  projected_margins_pending=projected_margins_pending,
                                  projected_margins_theoretical=projected_margins_theoretical)


class DefaultMarginProviderService(MarginProviderService):
    def __init__(self,
                 margin_calculator: MarginCalculator = IBMarginCalculator(),
                 broker_service: BrokerMarginServiceInterface = DbBrokerMarginService(),
                 margin_rates_cache_provider: MarginRatesCacheProvider = DBMarginRatesCashProvider(),
                 cash_provider_service: CashFlowProviderInterface = CashFlowProviderService(),
                 fx_spot_provider: FxSpotProvider = FxSpotProvider(),
                 hedge_position_service: HedgePositionService = HedgePositionService(),
                 margin_detail_service: MarginDetailServiceInterface = DbMarginDetailService(),
                 pnl_calculator: PnLCalculator = FxPnLCalculator(),
                 deposit_service: DepositService = DepositService(),
                 margin_multiplier=2.0):
        super().__init__(margin_calculator=margin_calculator,
                         broker_service=broker_service,
                         margin_rates_cache_provider=margin_rates_cache_provider,
                         cash_provider_service=cash_provider_service,
                         fx_spot_provider=fx_spot_provider,
                         hedge_position_service=hedge_position_service,
                         margin_detail_service=margin_detail_service,
                         pnl_calculator=pnl_calculator,
                         deposit_service=deposit_service,
                         margin_multiplier=margin_multiplier)


service = DefaultMarginProviderService()

class BacktestMarginProviderService(MarginProviderServiceInterface):
    def get_recommended_and_minimum_deposit(self, company: Company, date: Date, account_type: Account.AccountType,
                                            additional_cash: Optional[Dict[Currency, float]] = None,
                                            days_to_project: int = 30) -> Tuple[float, float]:
        return 0.0, 0.0

    def compute_margin_for_position(self, old_new_positions: PositionChange, company: Company, date: Date,
                                    account_type: Account.AccountType = Account.AccountType.LIVE,
                                    spot_fx_cache: Optional[SpotFxCache] = None) -> Optional[MarginDetail]:
        return None

    def get_margin_health_report(self, company: Company, custom_amount=None) -> Optional[MarginHealthReport]:
        return None

    def get_margin_detail(self,
                          company: Company,
                          date: Date,
                          account_type: Account.AccountType = Account.AccountType.LIVE) -> Optional[MarginDetail]:
        return None

    def compute_projected_margin(self,
                                 date: Date,
                                 company: Company,
                                 account_type: Account.AccountType = Account.AccountType.LIVE,
                                 additional_cash=None,
                                 days_to_project: int = 30) -> List[ProjectedMargin]:
        return []


