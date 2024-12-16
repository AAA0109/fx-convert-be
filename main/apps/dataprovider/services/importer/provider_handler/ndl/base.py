from abc import ABC

from django.db import models

from main.apps.broker.models import Broker
from main.apps.dataprovider.services.importer.provider_handler.handlers.json import JsonHandler
from main.apps.marketdata.models import DataCut
from main.apps.country.models import Country
from main.apps.currency.models import Currency


class NdlUrlHandler(JsonHandler, ABC):
    """
    NdlUrlHandler is a base class for handling data from NDL.

    types_to_fetch: a list containing all the types of data we want to fetch, with each type explained as follows:
    - 'CPI':  CPI (Standardized Global Economics - Consumer Price Index) data. The Consumer Price Index (CPI) is a measure of inflation related to the cost of living
    - 'CPIC': CPIC (Standardized Global Economics) data. CPIC measures the growth rate of prices and serves as an indicator of inflation.
    - 'G': GDP (Standardized Global Economics - Gross Domestic Product) data. GDP represents the unadjusted gross domestic product, which is the total value of all final goods and services produced within a country's borders in a specific time period.
    - 'GAGR': GAGR (Standardized Global Economics - GDP Annual Growth Rate) data. represents the annual growth rate of GDP (Gross Domestic Product).
    - 'EXVOL': EXVOL (Standardized Global Economics - Exports Volume) data. represents the total value of goods and services produced by a country and purchased by foreign entities.
    - 'IMVOL': IMVOL (Standardized Global Economics - Imports Volume) data. represents the total value of a country's imports of physical goods and payments to foreigners for services like shipping and tourism.
    - 'GPC': GPC (Standardized Global Economics - GDP per Capita) data. represents the Gross Domestic Product per capita, which is the GDP divided by the population of a country.
    - 'GPCP': GPCP (Standardized Global Economics - GDP per Capita PPP) data.represents the Gross Domestic Product per capita in terms of purchasing power parity (PPP), which measures the average GDP per person in international dollars.
    - 'IR': IR (Standardized Global Economics - Interest Rate) data. represents the daily average of the central bank policy rate
    - 'GPC': UNR (Standardized Global Economics - Unemployment Rate) data. represents the percentage of the labor force of a country who are unemployed and actively seeking work.
    """
    url: str
    types_to_fetch = ['CPI','CPIC','G', 'GAGR', 'EXVOL','IMVOL','GPC','GPCP','IR','UNR','CCONF','CSP','GDG','GSP','JOBOFF','JVAC','MKT','WAGE','WGGR']
    @staticmethod
    def _get_currency_id_map() -> dict:
        currencies = Currency.objects.all()
        mappings = {}
        for currency in currencies:
            mappings[currency.mnemonic] = currency
        return mappings

    @staticmethod
    def _get_country_code_list() -> dict:
        country_qs = Country.objects.filter(use_in_average=True)
        qs1_names = set(country_qs.values_list('currency_code', flat=True))
        currency_qs = Currency.objects.all()
        qs2_names = set(currency_qs.values_list('mnemonic', flat=True))
        common_names = qs1_names.intersection(qs2_names)
        countries = Country.objects.filter(
            currency_code__in=list(common_names), use_in_average=True)
        print(countries)
        result_dict = {}
        for country in countries:
            if country.currency_code not in result_dict:
                result_dict[country.currency_code] = [country.code]
            else:
                result_dict[country.currency_code].append(country.code)
        return result_dict


    def __init__(self, data_cut_type: DataCut.CutType, model: models.Model, url: str):
        super().__init__(data_cut_type=data_cut_type, model=model)
        self.url = url

    @staticmethod
    def _get_currency_code(country_name):
        try:
            country = Country.objects.get(code=country_name)
            return country.currency_code
        except Country.DoesNotExist:
            return None
