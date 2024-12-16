from abc import ABC
from typing import Union
import pandas as pd
import numpy as np
import datetime
import pytz
import re

from main.apps.dataprovider.services.importer.provider_handler.handlers.xlsx import XlsxHandler

from main.apps.currency.models import Currency
from main.apps.country.models import Country


class SpiHandler(XlsxHandler, ABC):

    def before_handle(self) -> pd.DataFrame:
        indicator_name_map = self.df[0:1].to_dict(orient='records')[0]
        currency_code_list = self._get_currency_code_list()
        country_currencycode_map = self._get_country_currencycode_map()
        name_description_map = self._get_name_description_map()
        rank_columns = self.df.columns.tolist()[6:]
        self.df = self.df.drop(0).reset_index(drop=True)
        avg_df = self._get_avg_df(self.df)
        rank_df = self._get_rank_df(self.df, rank_columns)

        self.df["currency_code"] = self.df["spicountrycode"].map(country_currencycode_map)
        self.df = self.df[self.df["currency_code"].isin(currency_code_list)]
        self.df.drop(columns=['rank_score_spi'], inplace=True)

        id_vars = ["country", "spicountrycode", "currency_code", "spiyear"]
        value_vars = list(self.df.columns[4:])
        self.df = pd.melt(self.df, id_vars=id_vars, value_vars=value_vars, var_name='indicator', value_name='value')
        self.df = pd.merge(self.df, rank_df, on=[
                           'spiyear', 'indicator', 'country'], suffixes=('_self', '_rank'), how='left')

        grouped = self.df.groupby(['currency_code', 'indicator'])
        same_currency_code_df = grouped.filter(lambda x: x['spicountrycode'].nunique() > 1)
        self.df.drop(same_currency_code_df.index, inplace=True)

        if not same_currency_code_df.empty:
            unique_currency_code_df = self._get_unique_currency_code(same_currency_code_df)
            self.df = pd.concat([self.df, unique_currency_code_df], ignore_index=True)

        self.df['name'] = self.df['indicator'].map(indicator_name_map)
        self.df['unit'] = self.df['name'].str.extract(r'(\([^)]*\))')
        self.df['name'] = self.df["name"].apply(lambda x: re.sub(r' \([^)]*\)', '', x)).str.strip()
        self.df['description'] = self.df['name'].map(name_description_map)

        self.df = self.df.sort_values(by=["currency_code", "country", "spiyear"]).reset_index(drop=True)
        self.df = self.df[["country", "spicountrycode", "currency_code", "spiyear",
                           "name", "unit", "description", "indicator", "value", "rank"]]

        self.df = self.df.merge(avg_df, on=['spiyear', 'indicator'], how='left')
        return self.df

    def transform_data(self) -> pd.DataFrame:
        self.df.index += 1
        currency_id_map = self._get_currency_id_map()
        self.df['currency_code'] = self.df['currency_code'].map(currency_id_map)
        self.df['value'] = pd.to_numeric(self.df['value'], errors='coerce')
        self.df['value'] = self.df['value'].round(2).replace({np.nan: None})
        self.df['parent_index'] = None
        self._set_parent_index()
        self.df["spiyear"] = self.df["spiyear"].apply(
            lambda x: pytz.timezone('UTC').localize(datetime.datetime(x, 1, 1)))
        return self.df

    @staticmethod
    def _get_currency_code_list() -> list:
        currencies = Currency.objects.values_list('mnemonic', flat=True)
        return list(currencies)

    @staticmethod
    def _get_country_currencycode_map() -> dict:
        countries = Country.objects.filter(currency_code__isnull=False, use_in_average=True).values('code', 'currency_code')
        mappings = {country['code']: country['currency_code'] for country in countries}
        return mappings

    def _get_name_description_map(self) -> dict:
        df_def = pd.read_excel(self.fpath, usecols='B:F', nrows=60, sheet_name="DEFINITIONS")
        df_def['Indicator name'] = df_def['Indicator name'].str.strip()
        indicator_definition_dict = df_def.set_index('Indicator name')['Definition'].to_dict()
        return indicator_definition_dict

    def _get_unique_currency_code(self, same_currency_code_df) -> pd.DataFrame:
        value_column_list = list(same_currency_code_df.columns)
        
        selected_columns = value_column_list[2:5]
        avg_df = same_currency_code_df.groupby(selected_columns)[['value', 'rank']].mean().reset_index()
        avg_df['rank'] = avg_df['rank'].apply(np.ceil).astype(int)
        avg_df['country'] = avg_df['currency_code'].apply(lambda x: x + '_avg')
        return avg_df

    def _get_rank_df(self, df, rank_columns) -> pd.DataFrame:
        result_df = pd.DataFrame()

        grouped = df.groupby('spiyear')
        for year, group in grouped:
            ranks = group[rank_columns].rank(
                ascending=False, method='first', na_option='keep').astype('Int64')
            ranks.columns = [col for col in ranks.columns]
            ranks['score_spi'] = group['rank_score_spi']
            ranks['country'] = group['country']
            ranks['spiyear'] = year
            result_df = pd.concat([result_df, ranks])

        id_vars = ["country", "spiyear"]
        value_vars = list(result_df.columns[:-2])
        result_df = pd.melt(result_df, id_vars=id_vars,
                            value_vars=value_vars, var_name='indicator', value_name='rank')
        return result_df

    def _get_avg_df(self, df) -> pd.DataFrame:
        df = df[df['spicountrycode'] == 'WWW']
        value_column_list = list(df.columns)
        avg_df = pd.melt(df, id_vars='spiyear',
                         value_vars=value_column_list[5:], var_name='indicator', value_name='avg_value')
        avg_df['avg_value'] = avg_df['avg_value'].fillna(0.0).round(2)
        return avg_df

    parent_child_dict = {
        'score_spi': ['score_bhn', 'score_fow', 'score_opp'],
        'score_bhn': ['score_nbmc', 'score_ws', 'score_sh', 'score_ps'],
        'score_fow': ['score_abk', 'score_aic', 'score_hw', 'score_eq'],
        'score_opp': ['score_pr', 'score_pfc', 'score_incl', 'score_aae'],
        'score_nbmc': ['nbmc_stunting', 'nbmc_infectiousdaly', 'nbmc_matmort', 'nbmc_childmort', 'nbmc_undernourish', 'nbmc_dietlowfruitveg'],
        'score_ws': ['ws_washmortdalys', 'ws_sanitation', 'ws_water', 'ws_watersat'],
        'score_sh': ['sh_hhairpolldalys', 'sh_affhousingdissat', 'sh_electricity', 'sh_cleanfuels'],
        'score_ps': ['ps_politicalkillings', 'ps_intpersvioldaly', 'ps_transportdaly', 'ps_intimpartnviol', 'ps_moneystolen'],
        'score_abk': ['abk_qualeduc', 'abk_propnoeduc', 'abk_popsomesec', 'abk_totprimenrol', 'abk_educpar'],
        'score_aic': ['aic_altinfo', 'aic_mobiles', 'aic_internet', 'aic_eparticip'],
        'score_hw': ['hw_qualityhealth', 'hw_lifex60', 'hw_ncdmort', 'hw_univhealthcov', 'hw_qualhealthsat'],
        'score_eq': ['eq_airpolldalys', 'eq_leadexpdalys', 'eq_pm25', 'eq_spindex'],
        'score_pr': ['pr_freerelig', 'pr_proprightswomen', 'pr_peaceassemb', 'pr_accessjustice', 'pr_freediscuss', 'pr_polrights'],
        'score_pfc': ['pfc_freedomestmov', 'pfc_earlymarriage', 'pfc_contracept', 'pfc_neet', 'pfc_vulnemploy', 'pfc_corruption'],
        'score_incl': ['incl_equalprotect', 'incl_equalaccess', 'incl_sexualorient', 'incl_accpubsersocgr', 'incl_gayslesb', 'incl_discrimin'],
        'score_aae': ['aae_acadfreed', 'aae_femterteduc', 'aae_tertschlife', 'aae_citabledocs', 'aae_qualuniversities']
    }

    def _set_parent_index(self):
        child_parent_dict = {}
        parent_index_dict = {}

        for parent, children in self.parent_child_dict.items():
            for child in children:
                child_parent_dict[child] = parent

        parent_groups = self.df.groupby(
            ['country', 'spiyear', self.df['indicator'].map(child_parent_dict)])

        for group_label, indices in parent_groups.groups.items():
            if len(indices) == 1:
                parent_index_dict[group_label] = None
            else:
                parent_index_dict[group_label] = int(self.df.loc[
                    (self.df['country'] == group_label[0]) &
                    (self.df['spiyear'] == group_label[1]) &
                    (self.df['indicator'] == group_label[2])
                ].index.tolist()[0])

        self.df['parent_index'] = self.df.apply(lambda row: parent_index_dict.get(
            (row['country'], row['spiyear'], child_parent_dict.get(row['indicator']))), axis=1)
        self.df['parent_index'] = self.df['parent_index'].astype('Int64')
