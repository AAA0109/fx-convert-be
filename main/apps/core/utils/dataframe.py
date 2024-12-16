from datetime import timedelta

import numpy as np
import pandas as pd

from main.apps.core.utils.date import datetime2str, str2datetime


def get_index(PDindex, date, strDate=False):
    date = str2datetime(date)
    index = None
    for _ in range(252):
        try:
            index = PDindex.get_loc(date)
        except:
            date = date + timedelta(days=1)
        if index != None:
            break
    else:
        print('not found!')
        return None

    if strDate:
        date = datetime2str(date)

    return index, date


def convert_nan_to_none(df: pd.DataFrame) -> pd.DataFrame:
    return df.where(pd.notnull(df), None)


def convert_none_to_nan(df: pd.DataFrame) -> pd.DataFrame:
    return df.where(pd.notnull(df), np.nan)


def convert_nat_to_none(df: pd.DataFrame) -> pd.DataFrame:
    return df.replace({pd.NaT: None})


def normalize_df_from_qs(df_from_qs: pd.DataFrame) -> pd.DataFrame:
    df_from_qs["date"] = df_from_qs["date"].dt.tz_localize(None)
    df_from_qs["date"] = df_from_qs["date"].apply(lambda x: x.replace(hour=0, minute=0, second=0))
    # df_from_qs = df_from_qs.sort_values(by=["date"])
    df_from_qs.set_index("date", inplace=True)
    df_from_qs.sort_index(inplace=True)
    df_from_qs = convert_none_to_nan(df_from_qs)
    return df_from_qs


def correct_values(df: pd.DataFrame):
    # ===================remove holiday=================================
    numNaN = df[['close', 'open', 'low', 'high']].isna().sum(axis=1)
    df.drop(df[numNaN > 2].index, inplace=True)

    # ====================fix the high and low===========================
    highLowSwitch = (df['high'] - df['low']) < 0
    newLowp = df['low'].where(~highLowSwitch, df['high']).copy()
    newHighp = df['high'].where(~highLowSwitch, df['low']).copy()

    df['low'] = newLowp
    df['high'] = newHighp

    zeroDist = (df['high'] - df['low']) == 0
    df['low'] = df['low'].where(~zeroDist, (1 - 0.0025) * df['low'])
    df['high'] = df['high'].where(~zeroDist, (1 + 0.0025) * df['high'])

    # ====================fix the close and open===========================
    for p in ['open', 'close']:
        higherThanHigh = (df['high'] - df[f'{p}']) < 0
        lowerThanLow = (df[f'{p}'] - df['low']) < 0

        df[f'{p}'] = df[f'{p}'].where(~higherThanHigh, df['high'])
        df[f'{p}'] = df[f'{p}'].where(~lowerThanLow, df['low'])
    return df


def interpolate_values(df: pd.DataFrame):
    return df.interpolate(method='linear', limit_direction='both', axis=0)
