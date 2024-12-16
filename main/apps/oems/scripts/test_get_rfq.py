import os
from unittest import skip

import requests


@skip("Test script exclude from unit test")
def run():
    # {'ticket_id': 'a68aaa3b-6ba7-4237-9ba3-6f1084b3a65f', 'transaction_id': '0ade903a-44d5-480b-96e6-65cc3580926e' }
    token = os.getenv('LOCAL_API_TOKEN', "1b0552936ec8d17d82b3f161b8dec5d2a126049e")
    url = 'http://127.0.0.1:8000/api/v2/oems/rfq/8bac2f21-46fe-4352-9eb0'  # -acc4a09aa0b1' # should end in 1

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Token {token}'
    }

    data = {
        'ticket_id': 'a68aaa3b-6ba7-4237-9ba3-6f1084b3a65f',
    }

    response = requests.get(url, headers=headers, json=data)

    print(response.status_code)

    try:
        print(response.json())
    except:
        pass
