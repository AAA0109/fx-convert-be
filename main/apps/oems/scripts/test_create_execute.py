import logging
import os
import time
import uuid
from datetime import date
from unittest import skipIf

import requests
from django.conf import settings

from main.apps.oems.models.ticket import Ticket

@skipIf(settings.APP_ENVIRONMENT != 'local',"Test script exclude from unit test")
def run(*args):
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - PID=%(process)d - TID=%(thread)d - %(message)s',
        level=logging.INFO)
    api_base = os.getenv('LOCAL_API_ENDPOINT', "https://api.internal.dev.pangea.io/api/v2")
    token = os.getenv('LOCAL_API_TOKEN', "1b0552936ec8d17d82b3f161b8dec5d2a126049e")

    url = f'{api_base}/oems/execute/'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'x-idempotency-key': str(uuid.uuid4()),
        'Authorization': f'Token {token}'
    }

    is_forward = 'fwd' in args
    value_date = '2024-09-16' if is_forward else date.today().isoformat()

    beneficiaries = {
        'eur': [{"beneficiary_id": 610268780000011003, "method": 'C' if is_forward else 'StoredValue',
                 "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
        'php': [{"beneficiary_id": "bad42294-16bf-48da-b6f4-60dfab7bc527"}]
        # 'usd': [{"beneficiary_id": 610268780002011002, "method": 'C' if is_forward else 'StoredValue',
        #          "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
        # 'cad': [{"beneficiary_id": 610268780000011001, "method": 'C' if is_forward else 'StoredValue',
        #          "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
        # 'kes': [{"beneficiary_id": 610324586000011043, "method": 'C' if is_forward else 'StoredValue',
        #          "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
    }

    settlement_info = {
        # 'usd': [{"settlement_account_id": 610268780002011002, "method": 'C' if is_forward else 'StoredValue',
        #          "payment_reference": 'TEST E2E'}],
        # 'eur': [{"settlement_account_id": 610268780000011003, "method": 'C' if is_forward else 'StoredValue',
        #          "payment_reference": 'TEST E2E'}]
        'usd': [{"settlement_account_id": "a73ee659-b53f-4368-8c0e-ec33601bcb69"}]
    }

    test_data = [
        # {"sell_currency": "USD", "buy_currency": "EUR", "amount": 100000, "lock_side": "USD",
        #  "beneficiaries": beneficiaries['eur'], "settlement_info": settlement_info['usd']},
        # {"sell_currency": "USD", "buy_currency": "EUR", "amount": 100000, "lock_side": "EUR",
        #  "beneficiaries": beneficiaries['eur'], "settlement_info": settlement_info['usd']},
        # {"sell_currency": "EUR", "buy_currency": "USD", "amount": 100000, "lock_side": "EUR",
        # "beneficiaries": beneficiaries['usd'], "settlement_info": settlement_info['eur']},
        # {"sell_currency": "EUR", "buy_currency": "USD", "amount": 100000, "lock_side": "USD",
        #     "beneficiaries": beneficiaries['usd'], "settlement_info": settlement_info['eur']},
        # {"sell_currency": "EUR", "buy_currency": "CAD", "amount": 100000, "lock_side": "EUR",
        #  "beneficiaries": beneficiaries['cad'], "settlement_info": settlement_info['eur']},
        # {"sell_currency": "EUR", "buy_currency": "CAD", "amount": 100000, "lock_side": "CAD",
        #  "beneficiaries": beneficiaries['cad'], "settlement_info": settlement_info['eur']}
        # {"sell_currency": "USD", "buy_currency": "KES", "amount": 100000, "lock_side": "USD",
        #  "beneficiaries": beneficiaries['kes'], "settlement_info": settlement_info['usd'],
        #  "execution_strategy": "bestx"}
        {"sell_currency": "USD", "buy_currency": "PHP", "amount": 100000, "lock_side": "USD",
         "beneficiaries": beneficiaries['php'], "settlement_info": settlement_info['usd'],
         "execution_strategy": "bestx"}
    ]

    for data in test_data:
        data.update({"value_date": value_date, "broker": "MONEX"})

    test_data2 = {
        "sell_currency": "USD",
        "buy_currency": "EUR",
        "amount": 100000,
        "lock_side": "EUR",
        "beneficiaries": [
            {"beneficiary_id": 610268780000011003, "method": 'C', "purpose_of_payment": 'PURCHASE OF GOOD(S)','amount': 50000},
            {"beneficiary_id": 610268780000011003, "method": 'C', "purpose_of_payment": 'INTERCOMPANY PAYMENT','amount': 50000}
        ],
        "settlement_info": settlement_info['usd'],
    }

    responses = []
    with requests.Session() as session:
        # for data in test_data:
        response = session.post(url, headers=headers, json=test_data)

        try:
            payload = response.json()
            print(payload)
            ticket_id = payload[0].get('ticket_id', None)
        except:
            raise

        print('EXECUTE CREATED:', response.status_code, payload)

        if False and 'nopoll' not in args:
            if response.status_code == 201:
                n = 0
                payload = None
                while n < 100:
                    url = f'{api_base}/oems/status/{ticket_id}'
                    response = session.get(url, headers=headers)
                    if response.status_code == 200:
                        payload = response.json()
                        print('EXECUTION READY:', payload)
                        break
                    elif response.status_code > 400:
                        print(response.json())
                        break
                    else:
                        time.sleep(5.0)
                        n += 1
                if payload and 'ticket_id' in payload:
                    ticket = Ticket.objects.get(ticket_id=payload['ticket_id'])
                    ticket.print()
