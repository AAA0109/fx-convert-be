from abc import ABC, abstractmethod
from typing import List
from django.db.models import Model
from django_bulk_load import bulk_upsert_models

from main.apps.currency.models.currency import Currency

class InverseAndTriangulateHandler(ABC):
    model: Model
    home_currency: Currency

    def __init__(self, model: Model, home_currency: Currency) -> None:
        self.model = model
        self.home_currency = home_currency

    @abstractmethod
    def get_pk_field_names(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def populate_inverse_data(self) -> List[Model]:
        raise NotImplementedError

    @abstractmethod
    def populate_triangulate_data(self) -> List[Model]:
        raise NotImplementedError

    def upsert_inverse_data(self) -> None:
        self.inverse_home_currency_based_data = self.populate_inverse_data()
        bulk_upsert_models(
            models=self.inverse_home_currency_based_data,
            pk_field_names=self.get_pk_field_names()
        )

    def upsert_triangulate_data(self) -> None:
        triangulate_data = self.populate_triangulate_data()
        bulk_upsert_models(
            models=triangulate_data,
            pk_field_names=self.get_pk_field_names()
        )

    def execute(self):
        self.upsert_inverse_data()
        self.upsert_triangulate_data()
