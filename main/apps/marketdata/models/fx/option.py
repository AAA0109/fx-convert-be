import gzip
import pickle
from typing import Optional

import pandas as pd
import redis
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as __

from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.models.marketdata import MarketData


class FxOptionBase(MarketData):
    class DataType(models.TextChoices):
        LOCAL_STORAGE = 'local_storage', __('Local Storage')
        SFTP = 'sftp', __('SFTP')
        GCS = 'gcs', __('Google Cloud Storage')

    pair = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False)
    acquired_date = models.DateField(default=timezone.now)
    storage_type = models.CharField(max_length=255, choices=DataType.choices)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.data_time}-{self.pair}"

    @classmethod
    def get_df(cls, pair_id: Optional[int] = None, data_cut_id: Optional[int] = None) -> pd.DataFrame:
        # Create a Redis connection
        redis_client = redis.Redis.from_url(settings.REDIS_URL)
        cache_key = f"{cls.__name__}_{pair_id}_{data_cut_id}"
        cached_data = redis_client.get(cache_key)

        if cached_data:
            df = pickle.loads(cached_data)
        else:
            df = cls._read_data_from_database(pair_id, data_cut_id)

            # Save the data to Redis
            cached_data = pickle.dumps(df)
            redis_client.set(cache_key, cached_data)

        return df

    # ==============PRIVATE METHODS=============================================
    @classmethod
    def _read_data_from_database(cls, pair_id: Optional[int] = None,
                                 data_cut_id: Optional[int] = None) -> pd.DataFrame:
        filter_ = {}
        if pair_id:
            filter_['pair_id'] = pair_id
        if data_cut_id:
            filter_['data_cut_id'] = data_cut_id
        fx_option_qs = cls.objects.filter(**filter_)

        dataframes = []

        for fx_option in fx_option_qs:
            file = fx_option.file
            if file.name.endswith('.csv.gz'):
                with gzip.open(file.open('rb'), 'rt') as f:
                    df = pd.read_csv(f)
                    dataframes.append(df)

        # Concatenate all dataframes
        if dataframes:
            df = pd.concat(dataframes, ignore_index=True)
        else:
            df = pd.DataFrame()

        return df


class FxOption(FxOptionBase):
    file = models.FileField(upload_to='data_store/option_by_date_and_pair', default=None, null=True, blank=True)


class FxOptionStrategy(FxOptionBase):
    file = models.FileField(upload_to='data_store/option_strategy_by_date_and_pair', default=None, null=True,
                            blank=True)
