from functools import lru_cache

from hdlib.TermStructures.DiscountCurve import DiscountCurve_ConstRate
from hdlib.TermStructures.ForwardCurve import FlatForwardCurve
from hdlib.Universe.Asset.FxAsset import FxAsset
from hdlib.Universe.Asset.IrAsset import IrAsset
from hdlib.DataProvider.Fx.FxCorrelations import FxCorrelations
from hdlib.DataProvider.Fx.FxSpotVols import FxSpotVols
from hdlib.Universe.Historical.HistUniverseProvider import HistUniverseProvider
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache
from hdlib.Universe.Universe import Universe, Date, DayCounter, DayCounter_HD
from hdlib.Core.Currency import Currency
from hdlib.Core.FxPair import FxPair as FxPairHDL

from main.apps.core.utils.cache import redis_func_cache
from main.apps.hedge.models import HedgeAccountSettings_DB
from main.apps.marketdata.models import DataCut
from main.apps.marketdata.services.data_cut_service import DataCutService
from main.apps.marketdata.services.fx.fx_option_provider import FxOptionStrategyProvider
from main.apps.marketdata.services.fx.fx_provider import FxForwardProvider, FxSpotProvider, FxVolAndCorrelationProvider
from main.apps.marketdata.services.ir.ir_provider import MdIrProviderService
from main.apps.currency.models.fxpair import FxPair, FxPairName
from main.apps.marketdata.models.ir.discount import IrCurve

from typing import List, Set, Iterable, Sequence, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class UniverseProvider(HistUniverseProvider):
    """
    Historical Universe Provider.
    Can construct historical universes on command for a supplied valuation date
    """

    def __init__(self,
                 ir_currencies: Set[Currency],
                 fx_pair_ids: Iterable[int] = None,
                 fx_pairs: Sequence[FxPair] = None,
                 fx_names: Sequence[FxPairName] = None,
                 dc=DayCounter_HD(),
                 fx_spot_provider: FxSpotProvider = FxSpotProvider(),
                 fx_forward_provider: FxForwardProvider = FxForwardProvider(),
                 fx_vol_and_corr_provider: FxVolAndCorrelationProvider = FxVolAndCorrelationProvider()):
        """
        Create a historical universe provider.
        """
        try:
            self._fx_pairs = []
            if fx_pairs:
                self._fx_pairs = fx_pairs
            elif fx_pair_ids:
                self._fx_pairs = FxPair.get_pairs(pair_ids=fx_pair_ids)
            elif fx_names:
                self._fx_pairs = [pair for pair in FxPair.get_pairs_by_name(fx_names=fx_names)]
            else:
                self._fx_pairs = [pair for pair in FxPair.get_pairs()]

        except Exception as e:
            raise RuntimeError(f"Error initializing FX Pairs: {e}")

        # Ensure that we didn't slip in e.g. USD/USD
        self._fx_pairs = [pair for pair in self._fx_pairs if pair.base_currency != pair.quote_currency]

        self._ir_currencies = ir_currencies
        try:
            self._curve_ids = IrCurve.get_ois_curve_id_by_currency(currencies=ir_currencies)
        except Exception:
            raise RuntimeError("Error getting the OIS curve ids by currency")
        self._dc = dc

        self._fx_spot_provider = fx_spot_provider
        self._fx_forward_provider = fx_forward_provider
        self._fx_vol_and_corr_provider = fx_vol_and_corr_provider

    def make_universe(self,
                      ref_date: Date,
                      bypass_errors: bool = False,
                      create_vols: bool = True,
                      create_corr: bool = True,
                      flat_forward: bool = False,
                      flat_discount: bool = False,
                      spot_fx_cache: Optional[SpotFxCache] = None) -> Universe:
        """
        Main Method to construct the Universe on a given date
        :param bypass_errors: bool, if true, then errors encountered when loading a particular component of
            universe will be ignored. If they are never needed later, then great, else you will get a RunTimeError
            at the time you try access them
        :return: Universe
        """
        u = Universe(ref_date=ref_date, dc=self._dc)
        logger.debug(f"Getting EOD cut for date {ref_date}.")
        eod_cut = DataCutService.get_last_eod_cut(date=ref_date, include_today=True)

        # Add IRAssets
        logger.debug(f"Loading ir assets on date {ref_date}")
        start_time = Date.now()
        self._load_ir_assets(u=u, bypass_errors=bypass_errors, flat_discount=flat_discount)
        ir_time = Date.now() - start_time
        logger.debug(f"Loaded ir assets in {ir_time} seconds.")

        # Add FxAssets
        logger.debug(f"Loading fx assets on date {ref_date}.")
        start_time = Date.now()
        self._load_fx_assets(u=u, bypass_errors=bypass_errors, flat_forward=flat_forward, spot_fx_cache=spot_fx_cache)
        fx_time = Date.now() - start_time
        logger.debug(f"Loaded fx assets in {fx_time} seconds.")

        # If we can fetch vols, we will be able to narrow down which pairs actually have spot correlations.
        # If a pair does not have spot vol, it will not have spot correlation.
        spot_correlation_pairs = self._fx_pairs

        if create_vols:
            try:
                logger.debug(f"Loading fx vols on date {ref_date}.")
                start_time = Date.now()
                vols = self._fx_vol_and_corr_provider.get_spot_vols_at_time(pairs=self._fx_pairs, time=u.time)
                # Convert vols from FxPair -> vol to string -> vol.
                vols_by_name = {pair.name: value for pair, value in vols.items()}

                u.fx_universe.fx_vols = FxSpotVols(ref_date=ref_date, vols=vols_by_name)
                vols_time = Date.now() - start_time
                logger.debug(f"Loaded fx vols in {vols_time} seconds")

                # Find which pairs had spot vols. These are the pairs that will have spot correlations.
                spot_correlation_pairs = list(set(vols.keys()).intersection(self._fx_pairs))
                # for pair in self._fx_pairs:
                #     if pair not in vols:
                #         spot_correlation_pairs.remove(pair)
                logger.debug(
                    f"Only keeping {len(spot_correlation_pairs)} pairs with spot correlations, since these are the "
                    f"pairs that had spot vol and were in the universe's FX pairs")

            except Exception as e:
                raise RuntimeError(f"Error loading the FX Spot Vols: {e}")

            if len(vols) < len(self._fx_pairs):
                logger.warning(f"Couldn't find vols for all {len(self._fx_pairs)} FX pairs, "
                               f"only found {len(vols)}")

        # Create FX correlation provider
        if create_corr:
            try:
                logger.debug(f"Loading fx correlations on date {ref_date}")
                start_time = Date.now()
                corrs = self._fx_vol_and_corr_provider.get_spot_correl_matrix(pairs=spot_correlation_pairs,
                                                                              data_cut=eod_cut)
                u.fx_universe.fx_corrs = FxCorrelations(ref_date=ref_date, instant_corr=corrs)
                corrs_time = Date.now() - start_time
                logger.debug(f"Loaded fx correlations in {corrs_time} seconds")
            except Exception as e:
                raise RuntimeError(f"Error loading the Correlations: {e}")

        return u

    def get_dates(self, start: Date, end: Date) -> Iterable[Date]:
        """
        Get the dates of available universes, between start and end (inclusive)
        These are in ascending order
        :param start: Date, the first date (won't return any dates before this)
        :param end: Date, the end date (won't return and dates after this)
        :return: List[Date], all available dates between start and end (inclusive)
        """
        raise NotImplemented

    def get_next_date(self, date: Date) -> Date:
        raise NotImplemented

    def get_top_date(self) -> Date:
        raise NotImplemented

    def get_all_dates(self) -> Iterable[Date]:
        raise NotImplemented

    def get_n_dates(self, start: Date, num_dates: int) -> Iterable[Date]:
        """
        Get the first N dates including and following the start date that are available universes. If there are fewer
        than N available dates on or after the start date, the the maximum possible number of dates will be returned.

        :param start: Date, the first date
        :param num_dates: int, the number of dates to return.
        :returns: Iterable[Date], the first N (or fewer if necessary) available dates, starting with the start date
        """
        raise NotImplementedError

    def get_n_uniform_dates(self, start: Date, num_dates: int) -> Iterable[Date]:
        """
        Get N dates including the start date that are as uniformly space out as possible from the dates available to
        the universe. If there are fewer than N available dates on or after the start date, the maximum possible
        number of dates will be returned.

        :param start: Date, the first date
        :param num_dates: int, the number of dates to return.
        :returns: Iterable[Date], the first N (or fewer if necessary) available dates, starting with the start date
        """
        raise NotImplementedError

    @property
    def day_counter(self) -> DayCounter:
        """ Get the day counter, used for all day counting internally """
        return self._dc

    # ================
    # Private
    # ================

    def _load_ir_assets(self,
                        u: Universe,
                        bypass_errors: bool = False,
                        flat_discount: bool = False):
        if flat_discount:
            for currency in self._ir_currencies:
                discount_curve = DiscountCurve_ConstRate(rate=0, ref_date=u.ref_date, dc=self._dc)
                asset = IrAsset(currency, discount_curve)
                u.add_ir_asset(asset)
        else:
            curve_ids: List[int] = list(self._curve_ids.values())

            discount_curves, _ = MdIrProviderService.get_most_recent_discount_curves(ir_curves=curve_ids,
                                                                                     time=u.ref_date,
                                                                                     dc=self._dc,
                                                                                     currencies=self._ir_currencies)

            # Need to do some additional work to get the currency from the curve id.
            currency_by_mnemonic = {curr.get_mnemonic(): curr for curr in self._ir_currencies}
            currency_by_id = {curve_id: currency_by_mnemonic[mnem] for mnem, curve_id in self._curve_ids.items()}

            for curve_id, curve in discount_curves.items():
                currency = currency_by_id[curve_id]
                if curve is None:
                    if not bypass_errors:
                        raise RuntimeError(f"error loading IR Asset for {currency.get_mnemonic()}")
                    else:
                        # Use a flat discount curve.
                        logger.warning(f"Couldn't load the IR curve for {currency.get_mnemonic()}, assuming 0 rate")
                        curve = DiscountCurve_ConstRate(rate=0, ref_date=u.ref_date, dc=self._dc)
                asset = IrAsset(currency, curve)
                u.add_ir_asset(asset)

    def _load_fx_assets(self,
                        u: Universe,
                        bypass_errors: bool = False,
                        flat_forward: bool = False,
                        spot_fx_cache: Optional[SpotFxCache] = None):

        if not spot_fx_cache:
            start_time = Date.now()
            spot_fx_cache = self._fx_spot_provider.get_spot_cache(time=u.ref_date, fxpairs=self._fx_pairs)
            logger.debug(f"  * Loaded spot fx cache in {Date.now() - start_time} seconds")

        # Get all forwards that we can.
        start_time = Date.now()
        all_fwds = FxForwardProvider.get_all_forward_curves(spot_cache=spot_fx_cache, look_back_days=5, fx_pairs=self._fx_pairs)
        logger.debug(f"  * Loaded all forwards in {Date.now() - start_time} seconds")

        # TODO: Get all forward values from the database at once, instead of once per pair.
        for fx_pair in self._fx_pairs:
            try:
                if flat_forward:
                    spot_fx = spot_fx_cache.get_fx(fx_pair=fx_pair)
                    fwd_curve = FlatForwardCurve(F0=spot_fx, ref_date=u.ref_date, dc=self._dc)
                else:
                    fwd_curve = all_fwds.get(fx_pair, None)

                if not fwd_curve:
                    if not bypass_errors:
                        raise RuntimeError(f"could not load forward for {fx_pair.name}")
                    continue
                asset = FxAsset(FxPairHDL.from_str(fx_pair.name), fwd_curve=fwd_curve)
                u.add_fx_asset(asset)
            except Exception as e:
                if not bypass_errors:
                    raise RuntimeError(f"Error Loading FX Asset for {fx_pair.name}: {e}")


class UniverseProviderService(object):
    """
    Service responsible for creating pricing universes for various purposes
    """

    def __init__(self,
                 fx_spot_provider: FxSpotProvider = FxSpotProvider(),
                 fx_forward_provider: FxForwardProvider = FxForwardProvider(),
                 fx_vol_and_corr_provider: FxVolAndCorrelationProvider = FxVolAndCorrelationProvider(),
                 fx_option_strategy_provider: FxOptionStrategyProvider = FxOptionStrategyProvider()):
        self._fx_spot_provider = fx_spot_provider
        self._fx_forward_provider = fx_forward_provider
        self._fx_vol_and_corr_provider = fx_vol_and_corr_provider
        self._fx_option_strategy_provider = fx_option_strategy_provider

    @property
    def fx_spot_provider(self) -> FxSpotProvider:
        return self._fx_spot_provider

    @property
    def fx_forward_provider(self) -> FxForwardProvider:
        return self._fx_forward_provider

    @property
    def fx_vol_and_corr_provider(self) -> FxVolAndCorrelationProvider:
        return self._fx_vol_and_corr_provider

    @property
    def fx_option_strategy_provider(self) -> FxOptionStrategyProvider:
        return self._fx_option_strategy_provider

    def make_cntr_currency_universes_by_domestic(self,
                                                 domestics: Set[Currency],
                                                 ref_date: Date,
                                                 bypass_errors: bool = False,
                                                 all_or_none: bool = False,
                                                 spot_fx_cache: Optional[SpotFxCache] = None
                                                 ) -> Dict[Currency, Universe]:
        """
        Make a collection of counter-currency universes
        :param domestics: Set[Currency], which domestic currencies to create universes for
        :param ref_date: Date, the reference date for the universe
        :param bypass_errors: bool, if True, allows individual universes to bypass errors (not fail) during
              construction
        :param all_or_none: bool, if True, a failure for any counter currency universe will lead to exception,
            else construct all that you can and log errors for failures
        :param spot_fx_cache: SpotFxCache, if supplied use these spots when creating universe
        :return: Dict[Currency, Universe], the universes by counter currency
        """
        universes: Dict[Currency, Universe] = {}
        for domestic in domestics:
            try:
                fx_pairs = FxPair.get_foreign_to_domestic_pairs(domestic=domestic)
                universes[domestic] = self.make_cntr_currency_universe(domestic=domestic,
                                                                       ref_date=ref_date,
                                                                       bypass_errors=bypass_errors,
                                                                       spot_fx_cache=spot_fx_cache,
                                                                       fx_pairs=tuple(fx_pairs))
            except Exception as e:
                if all_or_none:
                    raise e
                logger.error(f"Failed to create a universe for counter currency: {e}")

        return universes

    @redis_func_cache(key=None, timeout=60 * 60 * 20, delete=False)
    @lru_cache(typed=True, maxsize=2)
    def make_cntr_currency_universe(self,
                                    domestic: Currency,
                                    ref_date: Date,
                                    fx_pair_ids: Iterable[int] = None,
                                    fx_pairs: Sequence[FxPair] = None,
                                    bypass_errors: bool = False,
                                    create_vols: bool = True,
                                    create_corr: bool = True,
                                    flat_forward: bool = False,
                                    flat_discount: bool = False,
                                    spot_fx_cache: Optional[SpotFxCache] = None
                                    ) -> Universe:
        u = self.make_universe(ref_date=ref_date,
                               currencies={domestic},
                               fx_pair_ids=fx_pair_ids,
                               fx_pairs=fx_pairs,
                               bypass_errors=bypass_errors,
                               create_vols=create_vols,
                               create_corr=create_corr,
                               flat_forward=flat_forward,
                               flat_discount=flat_discount,
                               spot_fx_cache=spot_fx_cache
                               )
        u.cntr_currency = domestic  # Set so we know this is a counter currency universe.
        return u


    def make_universe(self,
                      currencies: Set[Currency],
                      ref_date: Date,
                      fx_pair_ids: List[int] = None,
                      fx_pairs: Iterable[FxPair] = None,
                      bypass_errors: bool = False,
                      create_vols: bool = True,
                      create_corr: bool = True,
                      flat_forward: bool = False,
                      flat_discount: bool = False,
                      spot_fx_cache: Optional[SpotFxCache] = None
                      ) -> Universe:
        try:
            up = UniverseProvider(fx_pairs=fx_pairs, fx_pair_ids=fx_pair_ids, ir_currencies=currencies,
                                  fx_forward_provider=self._fx_forward_provider,
                                  fx_spot_provider=self._fx_spot_provider,
                                  fx_vol_and_corr_provider=self._fx_vol_and_corr_provider)
        except Exception as e:
            raise RuntimeError(f"error initializing universe on {ref_date}: {e}")

        return up.make_universe(ref_date=ref_date,
                                bypass_errors=bypass_errors,
                                create_vols=create_vols,
                                create_corr=create_corr,
                                flat_forward=flat_forward,
                                flat_discount=flat_discount,
                                spot_fx_cache=spot_fx_cache
                                )
