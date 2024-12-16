import logging
import os
import time
import uuid
from datetime import date, timedelta
from unittest import skip

import requests

@skip("Test script exclude from unit test")
def run(*args):
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - PID=%(process)d - TID=%(thread)d - %(message)s',
        level=logging.INFO)

    api_base = os.getenv('LOCAL_API_ENDPOINT', "https://api.internal.dev.pangea.io/api/v2")

    with requests.Session() as session:

        token = os.getenv('LOCAL_API_TOKEN', "1b0552936ec8d17d82b3f161b8dec5d2a126049e")

        url = f'{api_base}/oems/execute/'

        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'x-idempotency-key': str(uuid.uuid4()),
            'Authorization': f'Token {token}'
        }

        if 'fwd' in args:
            vd = (date.today() + timedelta(94)).isoformat()
        else:
            vd = date.today().isoformat()  # spot

        data = {
            "sell_currency": "USD",
            "buy_currency": "INR",
            "amount": 100000,
            "lock_side": "USD",
            "value_date": 'EOM',
        }

        response = session.post(url, headers=headers, json=data)

        try:
            payload = response.json()
            print(payload)
            ticket_id = payload.get('ticket_id', None)
        except:
            raise

        print('EXECUTE CREATED:', response.status_code, payload)

        if 'nopoll' not in args:
            if response.status_code == 201:
                n = 0
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
