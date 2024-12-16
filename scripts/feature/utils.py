import os
from typing import Optional

import numpy as np
import pandas as pd
from hdlib.DateTime.Date import Date

from main.apps.currency.models import FxPair
from main.apps.marketdata.models import DataCut


def _get_filters(start_date: str, end_date: str, cut_type_list: list):
    _filter_params = {"data_cut__cut_type__in": cut_type_list}
    if start_date is not None:
        _filter_params["date__gte"] = Date.to_date(start_date)
    if end_date is not None:
        _filter_params["date__lte"] = Date.to_date(end_date)
    return _filter_params


def _extend_with_datacut(df_out: pd.DataFrame):
    datacut = pd.DataFrame(list(DataCut.objects.all().values())).rename(columns={"id": "data_cut_id"})
    df_out.reset_index(inplace=True, drop=True)
    df_out = pd.merge(df_out, datacut, on="data_cut_id", how="left")
    df_out["date"] = df_out["cut_time"].copy()
    df_out.set_index("date", inplace=True)
    return df_out


def _get_list_of_pairs():
    return ["EUR/USD",
            "GBP/USD",
            "USD/CAD",
            "USD/MXN",
            "USD/JPY",
            "AUD/USD",
            "USD/CNY",
            "USD/TRY",
            "USD/KRW",
            "USD/SGD",
            "USD/ZAR",
            "USD/IDR",
            "USD/INR",
            "USD/CHF",
            "USD/BRL",
            "USD/RUB",
            "USD/ANG",
            "USD/SAR",
            "USD/ARS",
            ]


def data_report(df_out, asset_id):
    _asset = FxPair.get_pair(asset_id)
    df_report = pd.DataFrame(
        columns=['data', 'start_date', 'end_date'])

    for i in df_out:
        column_name = str(_asset) + '_' + i
        tmp = df_out[[i]]
        print(column_name)

        if True if True in np.isnan(tmp.values) else False:
            nan_value = np.argwhere(np.isnan(tmp.values))
            nan_start = tmp.iloc[nan_value[0][0]].name
            nan_end = tmp.iloc[nan_value[-1][0]].name
            df = [column_name, nan_start, nan_end]

            df_report.loc[len(df_report)] = df

    return df_report


def extract_incorrect_date(df_out: pd.DataFrame):
    df_out.index = df_out.index.map(lambda timestamp: timestamp.replace(hour=0, minute=0, second=0, microsecond=0))
    start_date = df_out.index.min()
    end_date = df_out.index.max()

    # Generate business day range
    bday_range = pd.bdate_range(start=start_date, end=end_date)
    missing_days = bday_range.difference(df_out.index)
    missing_days_df = pd.DataFrame(missing_days, columns=['date'])
    missing_days_df["day"] = missing_days.day_name()
    missing_days_df.set_index("date", inplace=True)

    non_bdays = df_out.index[df_out.index.dayofweek > 4]
    non_bdays_df = pd.DataFrame(non_bdays, columns=['date'])
    non_bdays_df["day"] = non_bdays.day_name()
    non_bdays_df.set_index("date", inplace=True)

    return missing_days_df, non_bdays_df


def get_duplicated_values(df_out: pd.DataFrame):
    df = df_out.copy()
    df['date_group'] = df.index.date
    duplicated_dates = df.duplicated(subset='date_group', keep=False)
    duplicated_df = df[duplicated_dates]
    df_sorted = duplicated_df.sort_values(['date_group'], ascending=[True, ])
    return df_sorted


def get_data_anomaly(df: pd.DataFrame):
    print(f"start_date: {df.index.min()}")
    print(f"end_date: {df.index.max()}")
    missing_days_df, non_bdays_df = extract_incorrect_date(df)
    print(f"missing_days_df: {missing_days_df.shape[0]}")
    print(f"non_bdays_df: {non_bdays_df.shape[0]}")
    duplicated_dates = get_duplicated_values(df)
    print(f"Number of duplicated dates:{duplicated_dates['pair_id'].sum()}")
    return missing_days_df, non_bdays_df, duplicated_dates


def _get_spot_vol_forecast_pairs():
    return (
        "EUR/USD",
        "GBP/USD",
        "AUD/USD",
        "CAD/USD",
        "JPY/USD",
        "KRW/USD",
        "CHF/USD",
        "CNH/USD",
        "CNY/USD",
        "HKD/USD",
        "ILS/USD",
        "MXN/USD",
        "RUB/USD",
        "SAR/USD",
        "SGD/USD",
        "TRY/USD",
        "ZAR/USD",
        "IDR/USD",
        "INR/USD",
        "BRL/USD",
        "ANG/USD",
        "ARS/USD",
        "AED/USD",
        "CZK/USD",
        "DKK/USD",
        "HUF/USD",
        "NOK/USD",
        "NZD/USD",
        "PLN/USD",
        "SEK/USD",
        "THB/USD",
        "BRR/USD",
        "THO/USD",
        "IDF/USD",
        "INF/USD",
        "KES/USD",
        "KEF/USD",
        "PHP/USD",
        "PHF/USD",
        "TWD/USD",
        "TWF/USD",
        "TRF/USD",
        "MYR/USD",
        "MYF/USD",
        "AEF/USD",
        "KRF/USD",
    )


def _get_ai_forecaster_pairs():
    return (
        "EUR/USD",
        "GBP/USD",
        "AUD/USD",
        "CAD/USD",
        "JPY/USD",
        "KRW/USD",
        "CHF/USD",
        "CNY/USD",
        "HKD/USD",
        "ILS/USD",
        "MXN/USD",
        "SAR/USD",
        "SGD/USD",
        "TRY/USD",
        "ZAR/USD",
        "IDR/USD",
        "INR/USD",
        "BRL/USD",
        "AED/USD",
        "CZK/USD",
        "DKK/USD",
        "HUF/USD",
        "NOK/USD",
        "NZD/USD",
        "PLN/USD",
        "SEK/USD",
        "THB/USD",
        "BRR/USD",
        "THO/USD",
        "IDF/USD",
        "INF/USD",
        "KES/USD",
        "PHP/USD",
        "PHF/USD",
        "TWD/USD",
        "TWF/USD",
        "MYR/USD",
        "MYF/USD",
        "KRF/USD",
    )


def strip_date(date: str):
    if date is None:
        return ""
    return date.replace("-", "")


def get_dir_to_store_plot(
    marketdata_table: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    start_date_str = strip_date(start_date)
    end_date_str = strip_date(end_date)
    dir_name = f'/home/victor/victor/pangea/hedgedesk_dashboard/media/missing_data/{marketdata_table}/{start_date_str}_to_{end_date_str}/'
    os.makedirs(dir_name, exist_ok=True)
    return dir_name


def convert_missing_dates_to_ranges(df: pd.DataFrame) -> pd.DataFrame:
    # Sort by date
    df.sort_index(inplace=True)
    df['cut_time'] = df.index
    # Compute differences between consecutive dates
    df['diff'] = df['cut_time'].diff().dt.days

    condition_not_monday_and_diff_gt_1 = (df['day'] != 'Monday') & (df['diff'] > 1)
    condition_monday_and_diff_gt_3 = (df['day'] == 'Monday') & (df['diff'] > 3)
    df['transition'] = condition_not_monday_and_diff_gt_1 | condition_monday_and_diff_gt_3
    df.reset_index(inplace=True)
    missing_data_summary = {"missing_range": [], "start_date": [], "end_date": []}
    r = 1
    for idx in range(df.shape[0]):
        if idx == 0:
            start_date = df.loc[idx, 'cut_time']
        if idx == df.shape[0] - 1:
            end_date = df.loc[idx, 'cut_time']

            missing_data_summary["missing_range"].append(r)
            missing_data_summary["start_date"].append(start_date)
            missing_data_summary["end_date"].append(end_date)
            r += 1
            break
        transition = df.loc[idx, 'transition']
        next_transition = df.loc[idx + 1, 'transition']
        if transition == False and next_transition == True:
            end_date = df.loc[idx, 'cut_time']

            missing_data_summary["missing_range"].append(r)
            missing_data_summary["start_date"].append(start_date)
            missing_data_summary["end_date"].append(end_date)
            r += 1
            start_date = df.loc[idx + 1, 'cut_time']
        elif transition == True and next_transition == True:
            end_date = df.loc[idx, 'cut_time']
            missing_data_summary["missing_range"].append(r)
            missing_data_summary["start_date"].append(end_date)
            missing_data_summary["end_date"].append(end_date)
            r += 1
            start_date = df.loc[idx + 1, 'cut_time']
    return pd.DataFrame(missing_data_summary)
