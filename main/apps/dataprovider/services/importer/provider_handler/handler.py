import logging
from abc import ABC, abstractmethod
from typing import List, Sequence, Optional, Dict, Union, Pattern
import redis

import pandas as pd
from django.db import models
from django_bulk_load import bulk_upsert_models, bulk_update_models

from main.apps.currency.models import Currency
from main.apps.country.models import Country
from main.apps.marketdata.models import DataCut
from main.apps.core.utils.dataframe import convert_nan_to_none, convert_nat_to_none
from main.apps.marketdata.services.data_cut_service import DataCutService


class Handler(ABC):
    df: pd.DataFrame = None
    _data_cut_map: dict = {}

    def __init__(self, data_cut_type: DataCut.CutType = None):
        self.data_cut_type = data_cut_type
        self.redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

    @abstractmethod
    def execute(self):
        raise NotImplementedError

    def before_handle(self) -> pd.DataFrame:
        """ Before handle method - use this method to make changes to the DataFrame before import. You can add
        additional columns for the Mapping models here """
        return self.df

    def clean_data(self) -> pd.DataFrame:
        """ Data cleaning method - data cleaning and sanitization logic should be contained in this function"""
        self.df = convert_nan_to_none(self.df)
        self.df = convert_nat_to_none(self.df)
        return self.df

    def transform_data(self) -> pd.DataFrame:
        """ Data transformation method - data transform logic should be contained in this function"""
        return self.df

    def after_handle(self) -> pd.DataFrame:
        """ Override this method if further processing is needed on the dataframe after handle() is called """
        return self.df

    def handle(self):
        """ Data import method - import logic should be contained in this function"""
        self.add_data_cut_to_df()
        self.redis_create_or_update_records()
        self.create_or_update_records()

    def before_create_models_with_df(self):
        pass

    def redis_create_models_with_df(self):
        pass

    @abstractmethod
    def create_models_with_df(self) -> Sequence[models.Model]:
        raise NotImplementedError

    def after_create_models_with_df(self):
        pass

    def handle_updated_models(self, updated_models: Sequence[models.Model]):
        pass

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        """ Fields used to match existing models in the DB.
        By default uses model primary key. """
        return None

    def get_insert_only_field_names(self) -> Optional[Sequence[str]]:
        """ Names of model fields to only insert, never update (i.e. created_on) """
        return None

    def get_model_changed_field_names(self) -> Optional[Sequence[str]]:
        """ Fields that only get updated when another field (outside this
        list is changed) (i.e. update_on/last_modified) """
        return None

    def get_update_if_null_field_names(self) -> Optional[Sequence[str]]:
        """ Fields that only get updated if the new value is NULL or existing
        value in the DB is NULL. """
        return None

    def get_return_models(self) -> bool:
        """  Query and return the models in the DB, whether updated or not.
        Defaults to False, since this can significantly degrade performance """
        return False

    def get_update_pk_field_names(self) -> Optional[Sequence[str]]:
        """ Fields used to match existing models in the DB. When performing update.
        By default uses model primary key. """
        return None

    def get_update_update_field_names(self) -> Optional[Sequence[str]]:
        """ Field to update (defaults to all fields) """
        return None

    def get_update_model_changed_field_names(self) -> Optional[Sequence[str]]:
        """ Fields that only get updated when another field (outside this
        list is changed) (i.e. update_on/last_modified) """
        return None

    def get_update_update_if_null_field_names(self) -> Optional[Sequence[str]]:
        return None

    def get_update_return_models(self) -> bool:
        return False

    def redis_create_or_update_records(self) -> Dict[str, List[dict]]:
        """Revised to use Redis for data storage instead of PostgreSQL."""
        self.before_create_models_with_df()
        records = self.redis_create_models_with_df()
        self.after_create_models_with_df()

        updated_records = []

        # Iterate through each record and save it to Redis
        for record in records:
            # Use a unique key format based on your needs
            key = f"{self.data_cut_type}_{record['id']}"
            
            # Check if the record exists
            if self.redis_client.exists(key):
                existing_record = self.redis_client.hgetall(key)
                # If you need to perform any checks before updating
                updated_record = self._update_existing_record(existing_record, record)
                self.redis_client.hmset(key, updated_record)
                updated_records.append(updated_record)
            else:
                # New record, so add it to Redis
                self.redis_client.hmset(key, record)
                updated_records.append(record)

        return {
            "updated_records": updated_records
        }
    
    def _update_existing_record(self, existing_record: dict, new_record: dict) -> dict:
        """ Update existing record in Redis with new values. Customize as needed """
        for field, value in new_record.items():
            # Logic to determine how fields are updated
            if value is not None:
                existing_record[field] = value
        return existing_record
            
    def create_or_update_records(self) -> Dict[str, List[object]]:
        self.before_create_models_with_df()
        model_list = self.create_models_with_df()
        self.after_create_models_with_df()

        updated_models = bulk_upsert_models(
            models=model_list,
            pk_field_names=self.get_pk_field_names(),
            insert_only_field_names=self.get_insert_only_field_names(),
            model_changed_field_names=self.get_model_changed_field_names(),
            update_if_null_field_names=self.get_update_if_null_field_names(),
            return_models=self.get_return_models()
        )
        if self.get_return_models():
            updated_models = self.handle_updated_models(updated_models)
            bulk_update_models(
                models=updated_models,
                update_field_names=self.get_update_update_field_names(),
                pk_field_names=self.get_update_pk_field_names(),
                model_changed_field_names=self.get_update_model_changed_field_names(),
                update_if_null_field_names=self.get_update_update_if_null_field_names(),
                return_models=self.get_update_return_models()
            )

        return {
            "updated_models": updated_models
        }

    def add_data_cut_to_df(self):
        logger_logged = False
        last_logged_date = ''
        for index, row in self.df.iterrows():
            key = row['date'].__str__()
            if last_logged_date != key:
                logger_logged = False
            if not logger_logged:
                logging.info(f"get or create data cut for: {key}")
                last_logged_date = key
                logger_logged = True
            if key in self._data_cut_map:
                self.df.loc[index, 'DataCutId'] = self._data_cut_map[key]
            else:
                action_status, cut = DataCutService.create_cut(
                    row['date'], self.data_cut_type)
                if cut is not None:
                    self._data_cut_map[key] = cut.id
                    self.df.loc[index, 'DataCutId'] = self._data_cut_map[key]

        pass

    @staticmethod
    def _get_currency_regex() -> Union[Pattern, bool]:
        currencies = list(Currency.objects.all())
        if not len(currencies):
            return False
        regex = "("
        for currency in currencies:
            regex += currency.mnemonic
            if not currency == currencies[-1]:
                regex += '|'
        regex += ")"
        return regex

    @staticmethod
    def _get_currency_id_map() -> dict:
        currencies = Currency.objects.all()
        mappings = {}
        for currency in currencies:
            mappings[currency.mnemonic] = currency.id
        return mappings

