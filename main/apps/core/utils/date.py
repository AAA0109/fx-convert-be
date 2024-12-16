import re
from datetime import datetime
from typing import Union, Optional

import numpy as np
import pandas as pd
from dateutil.parser import parse
from pytz import timezone


def clean_date(text):
    datetimestr = parse(text)
    text = datetime.strptime(datetimestr, '%Y%m%d')
    return text


def reformat_date(date, tz='UTC', format='%m-%d-%y'):
    temp = date.str.split(r"/|-", n=-1, expand=True)
    for i in temp.columns:
        temp[i] = temp[i].str.slice(start=-2).str.zfill(2)
    return pd.to_datetime(temp.agg('-'.join, axis=1), format=format).apply(lambda x: x.tz_localize(tz))


def reformat_reuter_date(date: str, tz: str = 'UTC') -> Optional[datetime]:
    # todo: needs to be simplified
    date_match = re.search(r"(?P<month>\d?\d{1})/(?P<day>\d?\d{1})/(?P<year>\d{2})", date)
    if date_match is None:
        date_match = re.search(r"(?P<month>\d?\d{1})-(?P<day>\d?\d{1})-(?P<year>\d{2})", date)
    # for sep in ["/","-"]:
    #     pattern = r"(?P<month>\d?\d{1}){0}(?P<day>\d?\d{1}){1}(?P<year>\d{2})".format(sep,sep)
    #     date_match = re.search(pattern, date)
    #     if date_match is not None:
    #         break
    year = date_match.group('year')
    month = date_match.group('month')
    day = date_match.group('day')
    if float(year) >= 80:
        year = "19" + year
    else:
        year = "20" + year

    tz = timezone(tz)
    timestamp = datetime(
        int(year),
        int(month),
        int(day),
        17,
        0,
        0
    )
    timestamp = tz.localize(timestamp)
    return timestamp


def datetime2str(date_time_data: Union[datetime, str]) -> str:
    if isinstance(date_time_data, str):
        return date_time_data
    else:
        return date_time_data.strftime("%Y-%m-%d")


def str2datetime(date_time_data: Union[datetime, str]) -> datetime:
    if isinstance(date_time_data, datetime):
        return date_time_data
    else:
        return datetime.strptime(date_time_data, '%Y-%m-%d')


units = {"D": 1, "W": 7, "M": 30, "Y": 365, "ON": 0, "TN": 0, "SN": 1, "SW": 7}
regex = re.compile(r"(\d*)({0})".format("|".join(units.keys())))


def string2days(dts):
    if isinstance(dts,str):
        dts = regex.findall(dts)
        list_ = []
        for n, unit in dts:
            number = 1 if n == "" else float(n)
            list_.append(number * units[unit])
        return sum(list_)
    else:
        """in case of nan -> it will convert it to 0"""
        return 0


def get_date_format(date: str):
    for format in ["%m/%d/%Y %H:%M:%S", "%m/%d/%y %H:%M:%S", "%m-%d-%y %H:%M:%S"]:
        try:
            datetime.strptime(date, format)
            return format
        except:
            pass
    raise RuntimeError("date's format is not recognized")

def convert2datetime(date: str, time:str="00:00:00"):
    dt = f"{date} {time}"
    format = get_date_format(dt)
    return datetime.strptime(dt, format)
