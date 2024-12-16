from datetime import timedelta
from typing import List

import pandas as pd
from hdlib.DateTime.Date import Date

from main.apps.pricing.services.fee.product.pricing_strategy import Cashflow


def pack_cashflows_into_list(df: pd.DataFrame) -> List[Cashflow]:
    cashflows_list = []
    for index, row in df.iterrows():
        cashflow = Cashflow(value_date=row['value_date'], from_currency=row["from_currency"],
                            to_currency=row['to_currency'], from_amount=row['from_amount'])
        cashflows_list.append(cashflow)
    return cashflows_list


def get_sample_cashflows(from_currency: str = "USD", to_currency: str = "HUF") -> List[Cashflow]:
    cashflows = pd.DataFrame({
        "days": [30 * i for i in range(1, 7)],
        "from_amount": [2.738 for _ in range(6)],
        "from_currency": [from_currency for _ in range(6)],
        "to_currency": [to_currency for _ in range(6)],
    })

    base_date = Date.today()
    cashflows['value_date'] = cashflows['days'].apply(lambda x: base_date + timedelta(days=x))
    cashflows.drop('days', axis=1, inplace=True)
    return pack_cashflows_into_list(cashflows)
