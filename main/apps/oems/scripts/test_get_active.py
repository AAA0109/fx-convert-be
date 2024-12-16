from unittest import skip

import requests
from django.conf import settings


@skip("Test script exclude from unit test")
def run():
    token = settings.DASHBOARD_API_TOKEN
    url = 'https://api.internal.dev.pangea.io/api/v2/broker/ib/contract/active/XID'

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Token {token}'
    }

    response = requests.get(url, headers=headers)

    print(response.status_code)

    try:
        print(response.json())
    except:
        pass
