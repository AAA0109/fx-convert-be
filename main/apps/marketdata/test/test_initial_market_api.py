import logging

from collections import OrderedDict

from datetime import datetime
from rest_framework import status
from django.urls import reverse
from unittest import mock

from main.apps.payment.tests.base_payment_api_test import BasePaymentAPITest

logger = logging.getLogger(__name__)


class TestInitialMarketAPI(BasePaymentAPITest):

    def setUp(self) -> None:
        super().setUp()
        self.now = datetime.now()
        self.date_str = str(self.now.date())
        self.datetime_str = str(self.now).replace('+00:00', 'Z')

    def tearDown(self) -> None:
        super().tearDown()

    def get_initial_market_response_mock(self) -> dict:
        return {
            "market": "EURUSD",
            "rate_rounding": 4,
            "side": "Buy",
            "spot_date": self.date_str,
            "spot_rate": 1.1164,
            "rate": 1.1164,
            "fwd_points": 0.0,
            "fwd_points_str": "0.0 / 0.0%",
            "implied_yield": None,
            "indicative": True,
            "cutoff_time": None,
            "as_of": self.datetime_str,
            "status": {
                "market": "EURUSD",
                "recommend": True,
                "session": "NewYork",
                "execute_before": self.datetime_str,
                "unsupported": False
            },
            "channel_group_name": None,
            "fee": 0.0,
            "quote_fee": 0.005,
            "wire_fee": 10.0,
            "pangea_fee": "0.0 / 0.0%",
            "broker_fee": "0.0 / 0.0%",
            "all_in_reference_rate": 1.1164,
            "is_ndf": False,
            "fwd_rfq_type": 'api',
            "executing_broker": None,
            "is_same_currency": False
        }

    def get_recent_rate_response_mock(self) -> dict:
        return {
            "spot_rate": {
                "ask": 1.1164,
                "bid": 1.07133,
                "mid": 1.0934007505496564,
                "date": self.now
            },
            "fwd_points": {
                "ask": 0,
                "bid": 0,
                "mid": 0,
                "date": self.now
            },
            "channel_group_name": None
        }

    @mock.patch('main.apps.marketdata.services.initial_marketdata.get_initial_market_state')
    def test_initial_state_api(self, mock_initial_market_state):
        resp_mock = self.get_initial_market_response_mock()
        mock_initial_market_state.return_value = resp_mock
        payload = {
            'sell_currency': 'USD',
            'buy_currency': 'EUR',
            'value_date': self.date_str
        }

        # Test initial market state endpoint
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse("main:marketdata:initial-market-state"),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_200_OK, resp)
        resp1 = OrderedDict(sorted(resp.items()))
        resp2 = OrderedDict(sorted(resp_mock.items()))
        self.assertEqual(resp1, resp2, resp)

        # Test initial market state endpoint using 'SPOT' value date
        payload['value_date'] = 'SPOT'
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse("main:marketdata:initial-market-state"),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_200_OK, resp)
        self.assertEqual(resp, resp_mock, resp)


    @mock.patch('main.apps.marketdata.services.initial_marketdata.get_recent_data')
    def test_recent_rate_api(self, mock_recent_data):
        recent_rate = self.get_recent_rate_response_mock()
        mock_recent_data.return_value = (recent_rate['spot_rate'], recent_rate['fwd_points'], recent_rate['channel_group_name'])

        payload = {
            'sell_currency': 'USD',
            'buy_currency': 'EUR',
            'value_date': self.date_str
        }

        # Test recent rate endpoint
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse("main:marketdata:recent-market-rate"),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_200_OK, resp)

        # Test recent rate endpoint using 'SPOT' value date
        payload['value_date'] = 'SPOT'
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse("main:marketdata:recent-market-rate"),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_200_OK, resp)
