import logging
import os
import time
import uuid
from datetime import date, timedelta
from unittest import skip

import requests


@skip("Test script exclude from unit test")
def run(*args):
    # from main.apps.oems.backend.trading_utils import get_reference_data
    # ref = get_reference_data( 'BLAH' )
    # print( ref )
    # raise ValueError

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - PID=%(process)d - TID=%(thread)d - %(message)s',
        level=logging.INFO)

    api_base = os.getenv('LOCAL_API_ENDPOINT', "https://api.dev.pangea.io/api/v2")  # http://127.0.0.1:8000/api/v2

    is_forward = ('fwd' in args)

    beneficiaries = {
        'eur': [{"beneficiary_id": 610268780000011003, "method": 'C' if is_forward else 'StoredValue',
                 "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
        'usd': [{"beneficiary_id": 610268780002011002, "method": 'C' if is_forward else 'StoredValue',
                 "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
        'cad': [{"beneficiary_id": 610268780000011001, "method": 'C' if is_forward else 'StoredValue',
                 "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
        'jpy': [{"beneficiary_id": 610268780000011042, "method": 'C' if is_forward else 'StoredValue',
                 "purpose_of_payment": 'PURCHASE OF GOOD(S)'}],
        'mxn': [{"beneficiary_id": 610268780000011048, "method": 'C' if is_forward else 'StoredValue',
                 "purpose_of_payment": 'TEST E2E'}],
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

    with requests.Session() as session:

        token = os.getenv('LOCAL_API_TOKEN', "1b0552936ec8d17d82b3f161b8dec5d2a126049e")
        url = f'{api_base}/oems/rfq/'

        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-idempotency-key': str(uuid.uuid4()),
            'Authorization': f'Token {token}'
        }

        if is_forward:
            vd = (date.today() + timedelta(15)).isoformat()
            spot = False
        else:
            vd = date.today().isoformat()  # spot
            spot = True

        buy_ccy = 'EUR'
        sell_ccy = 'USD'

        data = {
            "sell_currency": sell_ccy,
            "buy_currency": buy_ccy,
            "amount": 1000000,
            "lock_side": buy_ccy,
            "value_date": vd if spot else '2024-08-06',
            "beneficiaries": beneficiaries.get(buy_ccy.lower()),
            "settlement_info": settlement_info.get(sell_ccy.lower()),
            'broker': 'MONEX',
        }

        print('PAYLOAD:', data)
        response = session.post(url, headers=headers, json=data)

        try:
            payload = response.json()
            ticket_id = payload.get('ticket_id', None)
        except:
            raise

        print('RFQ CREATED:', response.status_code, response.headers, payload)

        if 'refresh' in args:
            print('refresh quote')
            # data['value_date'] = '2024-06-03'
            data['tenor'] = 'spot'
            data['ticket_id'] = ticket_id

            response = session.post(url, headers=headers, json=data)
            print('RFQ REFRESHED:', response.status_code, response.json())

        if response.status_code == 201 and 'nopoll' not in args:
            n = 0
            while not payload['quote_expiry'] and n < 100:
                url = f'{api_base}/oems/status/{ticket_id}'
                response = session.get(url, headers=headers)
                if response.status_code == 200:
                    payload = response.json()
                    break
                elif response.status_code > 400:
                    print(response.json())
                    break
                else:
                    time.sleep(1.0)
                    n += 1

        if response.status_code == 200:
            print('RFQ READY:', payload)
            url = f'{api_base}/oems/execute-rfq/'
            if 'execute' in args:
                data = {
                    'ticket_id': ticket_id,
                }
                exc_resp = session.post(url, headers=headers, json=data)

                try:
                    payload = exc_resp.json()
                except:
                    raise

                print('EXECUTING RFQ:', response.status_code, payload)

                if exc_resp.status_code == 201:
                    n = 0
                    while payload['total_cost'] == 0.0 and n < 100:
                        url = f'{api_base}/oems/status/{ticket_id}'
                        response = session.get(url, headers=headers)
                        if response.status_code == 200:
                            payload = response.json()
                            break
                        elif response.status_code > 400:
                            payload = response.json()
                            break
                        else:
                            print('update', response.json())
                            time.sleep(3.0)
                        n += 1

                print('Execution Complete:', payload)
