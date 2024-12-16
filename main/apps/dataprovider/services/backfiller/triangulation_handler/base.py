from abc import ABC, abstractmethod

import pandas as pd
import pytz
from django.db.models import Q
from hdlib.AppUtils.log_util import get_logger, logging

from main.apps.currency.models import FxPair

logger = get_logger(level=logging.INFO)


class BaseTriangulationBackfiller(ABC):

    def __init__(self, triangulate_currency: str, home_currency: str, start_date: str, end_date: str):
        self.triangulate_currency = triangulate_currency
        self.home_currency = home_currency
        self.start_date = self._make_utc(pd.to_datetime(start_date)) if start_date else None
        self.end_date = self._make_utc(pd.to_datetime(end_date)) if end_date else None

    def execute(self):
        self._validate_pairs()
        all_pair_results = self._triangulate_all_pairs()
        all_reverse_pair_results = self._calculate_reverse_pairs(all_pair_results)

        self._upsert_instances(self._create_instances(all_pair_results))
        self._upsert_instances(self._create_instances(all_reverse_pair_results))

    # ===============PRIVATE METHODS================
    def _validate_pairs(self):
        triangulate_pairs = FxPair.objects.filter(
            (
                Q(base_currency__mnemonic=self.triangulate_currency) |
                Q(quote_currency__mnemonic=self.triangulate_currency)
            ) &
            ~Q(base_currency__mnemonic=self.home_currency) &
            ~Q(quote_currency__mnemonic=self.home_currency)
        )

        triangulate_pairs_list = [pair.name for pair in triangulate_pairs]
        pairs_without_reverse = []
        for pair in triangulate_pairs_list:
            fxpair = FxPair.get_inverse_pair(pair)
            if fxpair is None:
                pairs_without_reverse.append(pair)

        if pairs_without_reverse:
            raise Exception(f"Error: There are pairs without reverse {pairs_without_reverse}. Execution stopped.")
        else:
            logger.debug("All pairs have reverse.")

    @staticmethod
    def _make_utc(naive_date):
        """Convert a naive datetime object to UTC."""
        return naive_date.replace(tzinfo=pytz.utc)

    @abstractmethod
    def _triangulate_all_pairs(self):
        raise NotImplementedError

    @abstractmethod
    def _calculate_reverse_pairs(self, all_pair_results):
        raise NotImplementedError

    @abstractmethod
    def _upsert_instances(self, model_instances):
        raise NotImplementedError

    @abstractmethod
    def _create_instances(self, results):
        raise NotImplementedError
