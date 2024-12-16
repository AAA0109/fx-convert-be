import logging
import os
import time
import uuid
from datetime import date
from unittest import skip

import requests

from main.apps.oems.models.ticket import Ticket
from main.apps.oems.services.trading import trading_provider

@skip("Test script exclude from unit test")
def run(*args):
    # logging.basicConfig(
    #     format='%(asctime)s - %(name)s - %(levelname)s - PID=%(process)d - TID=%(thread)d - %(message)s',
    #     level=logging.INFO)
    logging.disable(logging.INFO)
    api_base = os.getenv('LOCAL_API_ENDPOINT', "https://api.internal.dev.pangea.io/api/v2")
    token = os.getenv('LOCAL_API_TOKEN', "1b0552936ec8d17d82b3f161b8dec5d2a126049e")

    from rest_framework.authtoken.models import Token
    token = Token.objects.get(key=token)
    user = token.user

    url = f'{api_base}/oems/execute/'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-idempotency-key': str(uuid.uuid4()),
        'Authorization': f'Token {token}'
    }

    is_forward = 'fwd' in args
    value_date = '2024-07-16' if is_forward else date.today().isoformat()

    beneficiaries = {
        'eur': [{"beneficiary_id": 610268780000011003, "method": 'C' if is_forward else 'StoredValue',
                 "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
        'usd': [{"beneficiary_id": 610268780002011002, "method": 'C' if is_forward else 'StoredValue',
                 "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
        'cad': [{"beneficiary_id": 610268780000011001, "method": 'C' if is_forward else 'StoredValue',
                 "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
        'jpy': [{"beneficiary_id": 610268780000011042, "method": 'C' if is_forward else 'StoredValue',
                 "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
    }

    settlement_info = {
        'usd': [{"settlement_account_id": 610268780002011002, "method": 'C' if is_forward else 'StoredValue',
                 "payment_reference": 'TEST E2E'}],
        'eur': [{"settlement_account_id": 610268780000011003, "method": 'C' if is_forward else 'StoredValue',
                 "payment_reference": 'TEST E2E'}],
        'cad': [{"settlement_account_id": 610268780000011001, "method": 'C' if is_forward else 'StoredValue',
                 "payment_reference": 'TEST E2E'}],
        'jpy': [{"settlement_account_id": 610268780000011042, "method": 'C' if is_forward else 'StoredValue',
                 "payment_reference": 'TEST E2E'}],
    }

    test_data = [

        # XXX/USD transactions
        {"sell_currency": "USD", "buy_currency": "EUR", "amount": 100000, "lock_side": "USD",
         "beneficiaries": beneficiaries['eur'], "settlement_info": settlement_info['usd']},
        {"sell_currency": "USD", "buy_currency": "EUR", "amount": 100000, "lock_side": "EUR",
         "beneficiaries": beneficiaries['eur'], "settlement_info": settlement_info['usd']},
        {"sell_currency": "EUR", "buy_currency": "USD", "amount": 100000, "lock_side": "EUR",
         "beneficiaries": beneficiaries['usd'], "settlement_info": settlement_info['eur']},
        {"sell_currency": "EUR", "buy_currency": "USD", "amount": 100000, "lock_side": "USD",
         "beneficiaries": beneficiaries['usd'], "settlement_info": settlement_info['eur']},

        # USD/XXX transactions
        {"sell_currency": "USD", "buy_currency": "JPY", "amount": 100000, "lock_side": "USD",
         "beneficiaries": beneficiaries['jpy'], "settlement_info": settlement_info['usd']},
        {"sell_currency": "USD", "buy_currency": "JPY", "amount": 100000, "lock_side": "JPY",
         "beneficiaries": beneficiaries['jpy'], "settlement_info": settlement_info['usd']},
        {"sell_currency": "JPY", "buy_currency": "USD", "amount": 100000, "lock_side": "JPY",
         "beneficiaries": beneficiaries['usd'], "settlement_info": settlement_info['jpy']},
        {"sell_currency": "JPY", "buy_currency": "USD", "amount": 100000, "lock_side": "USD",
         "beneficiaries": beneficiaries['usd'], "settlement_info": settlement_info['jpy']},

        # XXX/YYY
        {"sell_currency": "EUR", "buy_currency": "CAD", "amount": 100000, "lock_side": "EUR",
         "beneficiaries": beneficiaries['cad'], "settlement_info": settlement_info['eur']},
        {"sell_currency": "EUR", "buy_currency": "CAD", "amount": 100000, "lock_side": "CAD",
         "beneficiaries": beneficiaries['cad'], "settlement_info": settlement_info['eur']},
        {"sell_currency": "CAD", "buy_currency": "EUR", "amount": 100000, "lock_side": "EUR",
        "beneficiaries": beneficiaries['eur'], "settlement_info": settlement_info['cad']},
        {"sell_currency": "CAD", "buy_currency": "EUR", "amount": 100000, "lock_side": "CAD",
        "beneficiaries": beneficiaries['eur'], "settlement_info": settlement_info['cad']},

        #  XXX/YYY
        {"sell_currency": "JPY", "buy_currency": "CAD", "amount": 100000, "lock_side": "JPY",
         "beneficiaries": beneficiaries['cad'], "settlement_info": settlement_info['jpy']},
        {"sell_currency": "JPY", "buy_currency": "CAD", "amount": 100000, "lock_side": "CAD",
         "beneficiaries": beneficiaries['cad'], "settlement_info": settlement_info['jpy']},
        {"sell_currency": "CAD", "buy_currency": "JPY", "amount": 100000, "lock_side": "JPY",
        "beneficiaries": beneficiaries['jpy'], "settlement_info": settlement_info['cad']},
        {"sell_currency": "CAD", "buy_currency": "JPY", "amount": 100000, "lock_side": "CAD",
        "beneficiaries": beneficiaries['jpy'], "settlement_info": settlement_info['cad']}

    ]

    for data in test_data:
        # data.update({"value_date": value_date, "tenor": 'spot', "broker": "CORPAY", 'execution_strategy': 'bestx'})
        data.update({"value_date": value_date, "broker": "CORPAY"})

    ret = trading_provider.execute( user, test_data )
    print( ret )
