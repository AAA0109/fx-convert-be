import logging

from datetime import datetime, timedelta
from rest_framework import status
from django.urls import reverse
from main.apps.broker.models.broker import Broker
from main.apps.broker.models.constants import BrokerProviderOption
from main.apps.broker.models.fee import CurrencyFee
from main.apps.marketdata.models.ref.instrument import InstrumentTypes
from main.apps.oems.backend.xover import ensure_queue_table
from main.apps.payment.models.payment import ExecutionOptions, Payment
from main.apps.payment.tests.base_payment_api_test import BasePaymentAPITest

from unittest import mock

from main.apps.settlement.models import Beneficiary

LIST_CREATE_NAME = 'main:payment:payment-cashflow'

logger = logging.getLogger(__name__)

class TestInstallmentPaymentAPI(BasePaymentAPITest):

    def setUp(self) -> None:
        super().setUp()
        # ensure queue table global1 by default
        ensure_queue_table()
        provider = BrokerProviderOption.CORPAY
        corpay_broker = Broker(
            name=provider.capitalize(),
            broker_provider=provider
        )
        corpay_broker.save()
        self.corpay_usd_fee = CurrencyFee(broker=corpay_broker, buy_currency=self.usd, cost=0)
        self.corpay_eur_fee = CurrencyFee(broker=corpay_broker, buy_currency=self.euro, cost=0)
        self.corpay_usd_fee.save()
        self.corpay_eur_fee.save()
        self.mock_get_exec_config_eurusd_reponse = {
            "id": 568,
            "market": "EURUSD",
            "subaccounts": [
                "DU6108530"
            ],
            "staging": False,
            "default_broker": "CORPAY",
            "default_exec_strat": "MARKET",
            "default_hedge_strat": "SELFDIRECTED",
            "default_algo": "LIQUID_TWAP1",
            "spot_broker": "CORPAY",
            "fwd_broker": "CORPAY",
            "spot_rfq_type": "api",
            "fwd_rfq_type": "api",
            "spot_rfq_dest": "RFQ",
            "fwd_rfq_dest": "RFQ",
            "spot_dest": "CORPAY",
            "fwd_dest": "CORPAY",
            "use_triggers": True,
            "active": True,
            "min_order_size_from": 0.01,
            "max_order_size_from": 5000000,
            "min_order_size_to": 0.01,
            "max_order_size_to": 5000000,
            "max_daily_tickets": 100,
            "max_tenor": "1Y",
            "company": self.company.pk
        }


    def tearDown(self) -> None:
        return super().tearDown()

    def get_rate(self) -> dict:
        return {
            "rate": {
                "value": 1.1164,
                "lockSide": "Settlement",
                "rateType": "EURUSD",
                "operation": "Multiply"
            },
            "quoteId": "12345",
            "payment": {
                "currency": "EUR",
                "amount": 716.59
            },
            "settlement": {
                "currency": "USD",
                "amount": 800.0
            }
        }

    @mock.patch('main.apps.corpay.services.corpay.CorPayService.get_spot_rate')
    @mock.patch('main.apps.corpay.services.corpay.CorPayService.get_forward_quote')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.oems.backend.rfq_utils.calculate_corpay_fee')
    @mock.patch('main.apps.oems.backend.rfq_utils.get_recent_spot_rate')
    @mock.patch('main.apps.oems.validators.ticket.validate_instrument_amount')
    @mock.patch('main.apps.oems.validators.ticket.pangea_client.get_exec_config')
    @mock.patch('main.apps.approval.services.limit.CompanyLimitService.convert_to_company_currency')
    def test_non_schedule_payment_rfq_api(self, mock_conv_amnt, mock_get_exec_config2, mock_valid_amount, mock_spot_rate, mock_corpay_fee,
                                          mock_bene_validation, mock_get_ref_data, mock_get_exec_config,
                                          mock_corpay_fwd_rfq, mock_corpay_spot_rfq):
        mock_corpay_spot_rfq.return_value = self.get_rate()
        mock_corpay_fwd_rfq.return_value = self.get_rate()
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_get_exec_config2.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_bene_validation.return_value = True
        mock_corpay_fee.return_value = self.corpay_usd_fee
        mock_spot_rate.return_value = {
            'bid': 1.0884,
            'ask': 1.0878,
            'mid': 1.0881
        }
        mock_valid_amount.return_value = None
        mock_conv_amnt.return_value = self.mock_convert_amount

        now = datetime.now()

        payload = {
            "buy_currency": "USD",
            "destination_account_id": self.corpay_usd_fxbalance.account_number,
            "destination_account_method": "swift",
            "lock_side": "USD",
            "name": "GBPUSD Installment Payment",
            "origin_account_id": self.corpay_eur_fxbalance.account_number,
            "origin_account_method": "swift",
            "purpose_of_payment": Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS.value,
            "sell_currency": "EUR",
            "execution_timing": ExecutionOptions.IMMEDIATE_SPOT.value,
            "installments": [
                {
                    "date": str((datetime.utcnow() + timedelta(days=7)).date()),
                    "sell_currency": "EUR",
                    "buy_currency": "USD",
                    "amount": 800,
                    "cntr_amount": 751.39,
                    "lock_side": "USD"
                },
                {
                    "date": str((datetime.utcnow() + timedelta(days=14)).date()),
                    "sell_currency": "EUR",
                    "buy_currency": "USD",
                    "amount": 800,
                    "cntr_amount": 751.39,
                    "lock_side": "USD"
                }
            ],
        }

        # Test create payment endpoint
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED, resp)

        payment = resp.copy()

        # Test payment rfq endpoint
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse('main:payment:payment-rfq', kwargs={'pk':payment['id']})
        )
        tickets = resp['success']
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(tickets), 2)
        for ticket in tickets:
            self.assertIsNotNone(ticket['ticket_id'])
            self.assertIsNotNone(ticket['external_quote_expiry'])
            self.assertIsNotNone(ticket['external_quote'])

    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.oems.backend.rfq_utils.calculate_corpay_fee')
    @mock.patch('main.apps.oems.backend.rfq_utils.get_recent_spot_rate')
    @mock.patch('main.apps.oems.validators.ticket.get_best_execution_status')
    @mock.patch('main.apps.oems.validators.ticket.validate_instrument_amount')
    @mock.patch('main.apps.oems.validators.ticket.pangea_client.get_exec_config')
    @mock.patch('main.apps.approval.services.limit.CompanyLimitService.convert_to_company_currency')
    def test_schedule_payment_rfq_api(self, mock_conv_amnt, mock_get_exec_config2, mock_valid_amount, mock_best_x, mock_spot_rate,
                                      mock_corpay_fee, mock_bene_validation, mock_get_ref_data, mock_get_exec_config):
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_get_exec_config2.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_bene_validation.return_value = True
        mock_corpay_fee.return_value = self.corpay_usd_fee
        mock_spot_rate.return_value = {
            'bid': 1.0884,
            'ask': 1.0878,
            'mid': 1.0881
        }
        mock_best_x.return_value = self.get_best_x_mock()
        mock_valid_amount.return_value = None
        mock_conv_amnt.return_value = self.mock_convert_amount

        now = datetime.now()

        payload = {
            "amount": 100,
            "cntr_amount": 93.92,
            "buy_currency": "EUR",
            "delivery_date": str(now.date()),
            "destination_account_id": "1234",
            "fee_in_bps": 20,
            "fee": 0.2,
            "lock_side": "EUR",
            "name": "USDEUR OneTime Payment",
            "origin_account_id": "4321",
            "purpose_of_payment": Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS.value,
            "sell_currency": "USD",
            "execution_timing": ExecutionOptions.SCHEDULED_SPOT.value
        }

        # Test create payment endpoint
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)

        payment = resp.copy()

        # Test payment rfq endpoint
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse('main:payment:payment-rfq', kwargs={'pk':payment['id']})
        )
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

