from unittest.mock import patch, Mock

import pytest
from django.shortcuts import reverse

from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.models import TradingCalendarFincal
from main.apps.oems.backend.calendar_utils import *


@pytest.mark.django_db
def test_get_non_settlement_days(client, create_user, create_auth_headers, create_pair, add_trading_holiday):
    pair = create_pair('USD', 'CAD')  # type: FxPair
    user = create_user()
    headers = create_auth_headers(user=user)
    data = {
        'start_date': date.today(),
        'end_date': date.today() + timedelta(days=5),
        'sell_currency': pair.base_currency,
        'buy_currency': pair.quote_currency,
    }
    url = reverse('main:oems:non-settlement-days')

    # call with zero item
    response = client.post(url, data, headers=headers)
    assert response.status_code == 200 and response.json() == [], f'Invalid response: {response.content}'

    # call with 1 item
    dt = date.today()
    add_trading_holiday(code='NYB', holiday_date=dt)
    response = client.post(url, data, headers=headers)
    assert response.status_code == 200 and response.json() == [dt.isoformat()], \
        f'Invalid response: {response.content}'


@pytest.mark.django_db
def test_get_settlement_days(client, create_user, create_auth_headers, create_pair, add_trading_holiday):
    pair = create_pair('USD', 'CAD')  # type: FxPair
    user = create_user()
    headers = create_auth_headers(user=user)
    num_days = 7
    data = {
        'start_date': date.today(),
        'end_date': date.today() + timedelta(days=num_days),
        'sell_currency': pair.base_currency,
        'buy_currency': pair.quote_currency,
    }
    url = reverse('main:oems:settlement-days')

    holiday = None
    working_days = []

    for i in range(8):  # 7+1
        dt = date.today() + timedelta(days=i)
        if not dt.weekday() < 5:  # weekend
            continue

        if not holiday:  # add holiday at the 1st week day
            holiday = dt
            continue

        working_days.append(dt.strftime("%Y-%m-%dT%H:%M:%SZ"))

    add_trading_holiday(code='NYB', holiday_date=holiday)
    response = client.post(url, data, headers=headers)
    assert response.status_code == 200 and response.json() == working_days, \
        f'Invalid response: {response.content}'


@pytest.mark.django_db
def test_is_valid_settlement_day(client, create_user, create_auth_headers, create_pair, add_trading_holiday):
    pair = create_pair('USD', 'CAD')  # type: FxPair
    user = create_user()
    headers = create_auth_headers(user=user)
    data = {
        'date': None,
        'sell_currency': pair.base_currency,
        'buy_currency': pair.quote_currency,
    }
    url = reverse('main:oems:valid-settlement-day')

    holiday = None
    weekend = None
    work_day = None

    for i in range(8):  # 7+1
        dt = date.today() + timedelta(days=i)
        if not dt.weekday() < 5:  # weekend
            weekend = dt
            continue

        if not holiday:  # add holiday at the 1st week day
            holiday = dt
            continue
        work_day = dt

    # Test holiday
    data['date'] = holiday
    add_trading_holiday(code='NYB', holiday_date=holiday)
    response = client.post(url, data, headers=headers)
    assert response.status_code == 200 and response.json() == False, \
        f'Invalid response: {response.content}'

    # Weekend
    data['date'] = weekend
    response = client.post(url, data, headers=headers)
    assert response.status_code == 200 and response.json() == False, \
        f'Invalid response: {response.content}'

    # working day
    data['date'] = work_day
    response = client.post(url, data, headers=headers)
    assert response.status_code == 200 and response.json() == True, \
        f'Invalid response: {response.content}'


@pytest.mark.django_db
@pytest.mark.parametrize(
    "check_at", [
        ('next'),
        ('prev'),
    ]
)
def test_next_prev_valid_settlement_day(client, create_user, create_auth_headers, create_pair, add_trading_holiday,
                                        check_at):
    """
    Test of next_valid_settlement_day and prev_valid_settlement_day
    """

    pair = create_pair('USD', 'CAD')  # type: FxPair
    user = create_user()
    headers = create_auth_headers(user=user)
    data = {
        'date': None,
        'sell_currency': pair.base_currency,
        'buy_currency': pair.quote_currency,
    }
    holiday = None
    weekend = None

    for i in range(8):  # 7+1
        dt = date.today() + timedelta(days=i)
        if not dt.weekday() < 5:  # weekend
            weekend = dt
            continue

        if weekend and not holiday:  # add holiday at the monday
            holiday = dt
            break

    # Test holiday
    last_work_day = holiday - timedelta(days=3)  # friday
    add_trading_holiday(code='NYB', holiday_date=holiday)
    next_work_day = holiday + timedelta(days=1)  # tuesday

    if check_at == 'next':
        data['date'] = last_work_day
        check_date = next_work_day
        url = reverse('main:oems:next-valid-settlement-day')
    elif check_at == 'prev':
        data['date'] = holiday
        check_date = last_work_day
        url = reverse('main:oems:prev-valid-settlement-day')
    else:
        raise NotImplemented()

    response = client.post(url, data, headers=headers)
    assert response.status_code == 200 and response.json() == check_date.strftime("%Y-%m-%d"), \
        f'Invalid response: {response.content}'


@pytest.mark.django_db
@pytest.mark.parametrize(
    "check_at", [
        ('current'),
        ('next'),
    ]
)
def test_next_current_mkt_session(client, create_user, create_auth_headers, create_pair, check_at):
    """
    Test of get_current_mkt_session and get_next_mkt_session
    """
    pair = create_pair('USD', 'CAD')  # type: FxPair
    user = create_user()
    headers = create_auth_headers(user=user)
    curr_date = date.today()
    data = {
        'date': curr_date,
        'sell_currency': pair.base_currency,
        'buy_currency': pair.quote_currency,
    }

    if check_at == 'next':
        url = reverse('main:oems:next-mkt-day')
        gmtt_open = (curr_date + timedelta(days=1))
        gmtt_close = (curr_date + timedelta(days=2))
    else:
        url = reverse('main:oems:current-mkt-day')
        gmtt_open = (curr_date - timedelta(days=1))
        gmtt_close = (curr_date + timedelta(days=1))

    TradingCalendarFincal.objects.create(
        trade_date=curr_date.strftime("%Y-%m-%d"),
        activity='Synthetic Continuous Trading',
        gmtt_open=gmtt_open.strftime("%Y-%m-%dT%H:%M:%SZ"),
        gmtt_close=gmtt_close.strftime("%Y-%m-%dT%H:%M:%SZ"),
        cen_code='DCCE',
        functions='1 2 3 4L 4M 9F',
        market='Exec Deliverable Currencies'
    )

    check_data = [
        {
            'trade_date': curr_date.strftime("%Y-%m-%d"),
            'activity': 'Synthetic Continuous Trading',
            'gmtt_open': gmtt_open.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'gmtt_close': gmtt_close.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    ]

    response = client.post(url, data, headers=headers)
    assert response.status_code == 200 and response.json() == check_data, \
        f'Invalid response: {response.content}'


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tenor", [
        # ('SPOT'),
        # ('SN'),
        # ('SW'),
        # ('EOM1'),
        # ('EOM2'),
        ('EOM3'),
    ]
)
@patch('main.apps.oems.backend.calendar_utils.date', Mock(today=date(2024, 3, 8)))
@patch('main.apps.oems.backend.calendar_utils.datetime',
       Mock(now=datetime(2024, 3, 8, 12, tzinfo=pytz.timezone('America/New_York'))))
def test_get_fx_settlement_info(client, create_user, create_auth_headers, create_pair, add_trading_holiday, tenor):
    """
    Test of get_fx_settlement_info
    """
    pair = create_pair('USD', 'CAD')  # type: FxPair
    user = create_user()
    headers = create_auth_headers(user=user)
    curr_date = datetime(2024, 3, 8, 9, 15)
    add_trading_holiday(code='NYB', holiday_date=datetime(2024, 3, 11))  # holiday at monday / spot date

    url = reverse('main:oems:fx-settlement-info')
    data = {
        'date': curr_date,
        'tenor': tenor,
        'sell_currency': pair.base_currency,
        'buy_currency': pair.quote_currency,
    }

    if tenor == 'SPOT':
        check_data = {
            'days': 0,
            'ref_date': '2024-03-08',
            'settle_date': '2024-03-12',
            'spot_date': '2024-03-12',
            'tenor': 'SPOT',
        }
    elif tenor == 'SN':
        check_data = {
            'days': 1,
            'ref_date': '2024-03-08',
            'settle_date': '2024-03-13',
            'spot_date': '2024-03-12',
            'tenor': 'SN',
        }
    elif tenor == 'SW':
        add_trading_holiday(code='NYB', holiday_date=datetime(2024, 3, 19))  # holiday at settle day
        check_data = {
            'days': 8,  # min 7 + 1 holiday at settle_day
            'ref_date': '2024-03-08',
            'settle_date': '2024-03-20',
            'spot_date': '2024-03-12',
            'tenor': 'SW',
        }
    elif tenor == 'EOM1':
        add_trading_holiday(code='NYB', holiday_date=datetime(2024, 3, 29))  # holiday at settle day
        check_data = {
            'days': 16,
            'ref_date': '2024-03-08',
            'settle_date': '2024-03-28',
            'spot_date': '2024-03-12',
            'tenor': 'EOM1',
        }
    elif tenor == 'EOM2':
        add_trading_holiday(code='NYB', holiday_date=datetime(2024, 3, 29))  # holiday at settle day
        check_data = {
            'days': 49,
            'ref_date': '2024-03-08',
            'settle_date': '2024-04-30',
            'spot_date': '2024-03-12',
            'tenor': 'EOM2',
        }
    elif tenor == 'EOM3':
        add_trading_holiday(code='NYB', holiday_date=datetime(2024, 3, 29))  # holiday at settle day
        check_data = {
            'days': 80,
            'ref_date': '2024-03-08',
            'settle_date': '2024-05-31',
            'spot_date': '2024-03-12',
            'tenor': 'EOM3',
        }

    response = client.post(url, data, headers=headers)
    assert response.status_code == 200 and response.json() == check_data, \
        f'Invalid response: {response.content}'
