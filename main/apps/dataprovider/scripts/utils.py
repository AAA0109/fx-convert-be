from datetime import datetime

import numpy as np
import pandas as pd
from pytz import timezone

from main.apps.marketdata.models import DataCut

utc_tz = timezone('UTC')
eastern_tz = timezone('US/Eastern')


def extract_incorrect_date(df_in: pd.DataFrame):
    df_out = df_in.copy()
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


def get_ids_that_follow_dst_rules(df: pd.DataFrame):
    correct_ids = ((df['hour'] == 21) & (df['is_dst'] == True)) | (
        (df['hour'] == 22) & (df['is_dst'] == False))
    incorrect_ids = ~correct_ids
    return correct_ids, incorrect_ids


def split_data_based_on_dst_rules(df: pd.DataFrame):
    correct_ids, incorrect_ids = get_ids_that_follow_dst_rules(df)
    incorrect_data = df[incorrect_ids]
    correct_data = df[correct_ids]
    return correct_data, incorrect_data


def remove_duplicates(
    df_all_duplicates: pd.DataFrame,
    qs_each_kind,
    df: pd.DataFrame,
    revision_df: pd.DataFrame,

):
    if not df_all_duplicates['date_group'].is_unique:
        print("REMOVAL PROCESS")
        df_kept, df_removed = split_data_based_on_dst_rules(df_all_duplicates)
        qs_removed = qs_each_kind.filter(id__in=df_removed["marketdata_id"].tolist())
        print(f"Removed {qs_removed.count()} duplicated dates")
        qs_removed.delete()

    else:
        print("NO REMOVAL PROCESS")
        # this is the condition we need to meet
        correct_data, incorrect_data = split_data_based_on_dst_rules(df)

        if not incorrect_data.empty:
            print("THERE ARE STILL INCORRECT DATACUT")
            are_identical = sorted(incorrect_data["data_cut_id"].tolist()) == sorted(
                revision_df["data_cut_id"].tolist())
            print("IDENTICAL WITH THE INCORRECTS IN THE DATACUT TABLE:", are_identical)

            # Convert the lists to sets
            set1 = set(incorrect_data["data_cut_id"].tolist())
            set2 = set(revision_df["data_cut_id"].tolist())
            # Check if set1 is a subset of set2
            is_subset = set1.issubset(set2)
            print("SUBSET TO THE INCORRECTS IN THE DATACUT TABLE:", is_subset)


def is_dst(dt: datetime) -> bool:
    """
    Check if a given datetime is in Daylight Saving Time (DST) in Eastern Time.

    The function handles datetime objects in UTC, Eastern Time, or naive datetime objects
    (which are treated as UTC).

    Args:
    dt (datetime): A datetime object which could be in UTC, Eastern Time, or naive.

    Returns:
    bool: True if the datetime is in DST for Eastern Time, False otherwise.
    """
    # If dt is naive (no timezone), assume it's in UTC
    if dt.tzinfo is None:
        dt = utc_tz.localize(dt)

    dt_eastern = dt.astimezone(eastern_tz)
    return bool(dt_eastern.dst())


def get_all_related_objects(instance):
    related_objects_dict = {}

    for field in instance._meta.get_fields():
        # Check if the field is a reverse relation
        if (field.one_to_many or field.one_to_one) and field.auto_created and not field.concrete:
            # The related manager name is the lowercased model name
            related_manager = getattr(instance, field.get_accessor_name())
            # Get a QuerySet of related objects
            related_objects = related_manager.all()
            # Collect related objects in a dictionary
            related_objects_dict[field.related_model.__name__] = related_objects

    return related_objects_dict


def get_revision_df():
    cut_types = [
        DataCut.CutType.EOD,
    ]
    datacut_qs = DataCut.objects.filter(cut_type__in=cut_types)
    datacut_df = pd.DataFrame(list(datacut_qs.values())).rename(columns={"id": "data_cut_id"})
    datacut_df.reset_index(inplace=True, drop=True)
    datacut_df['hour'] = datacut_df["cut_time"].dt.hour
    datacut_df['date_group'] = datacut_df["cut_time"].dt.date
    datacut_df['is_dst'] = datacut_df["cut_time"].apply(is_dst)

    duplicated_dates = datacut_df.duplicated(subset='date_group', keep=False)
    duplicated_df = datacut_df[duplicated_dates]
    df_sorted = duplicated_df.sort_values(['date_group', 'hour'], ascending=[True, False])

    correct_ids, incorrect_ids = get_ids_that_follow_dst_rules(df_sorted)
    df_sorted['is_wrong_cut_id'] = incorrect_ids

    df_sorted['correct_datacut_id'] = np.nan
    for date in df_sorted['date_group'].unique():
        c = df_sorted[df_sorted['date_group'] == date]
        if c.shape[0] != 2:
            raise Exception(f"{date} does not have 2 datacuts")

        wrong_datacut_id = int(c[c['is_wrong_cut_id'] == True]["data_cut_id"].values[0])
        correct_datacut_id = int(c[c['is_wrong_cut_id'] == False]["data_cut_id"].values[0])

        df_sorted.loc[df_sorted['data_cut_id'] == wrong_datacut_id, "correct_datacut_id"] = correct_datacut_id

    revision_df = df_sorted.copy()
    revision_df.dropna(subset=['correct_datacut_id'], inplace=True)
    revision_df['correct_datacut_id'] = revision_df['correct_datacut_id'].astype(int)
    print("done")
    return revision_df, df_sorted
