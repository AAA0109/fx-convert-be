from datetime import datetime, timedelta
from unittest import mock
from django.urls import reverse
from rest_framework import status

from main.apps.payment.models.payment import ExecutionOptions, Payment
from main.apps.payment.tests.base_payment_api_test import BasePaymentAPITest
from main.apps.settlement.models import Beneficiary


class TestInstallmentPaymentAPI(BasePaymentAPITest):

    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.approval.services.limit.CompanyLimitService.convert_to_company_currency')
    def test_installment_payment_api(self, mock_conv_amnt, mock_bene_validation, mock_get_ref_data, mock_get_exec_config):
        LIST_CREATE_NAME = 'main:payment:payment-cashflow'
        RET_UPD_DEL_NAME = 'main:payment:payment-cashflow-with-pk'

        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_conv_amnt.return_value = self.mock_convert_amount

        now = datetime.now()
        date1 = now + timedelta(days=7)
        date2 = now + timedelta(days=14)

        payload = {
            "buy_currency": "USD",
            "destination_account_id": "1234",
            "lock_side": "USD",
            "name": "GBPUSD Installment Payment",
            "origin_account_id": "4321",
            "purpose_of_payment": Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS.value,
            "sell_currency": "GBP",
            "execution_timing": ExecutionOptions.IMMEDIATE_SPOT.value,
            "installments": [
                {
                    "date": str(now.date()),
                    "sell_currency": "GBP",
                    "buy_currency": "USD",
                    "amount": 500,
                    "cntr_amount": 401.27,
                    "lock_side": "USD"
                },
                {
                    "date": str(date1.date()),
                    "sell_currency": "GBP",
                    "buy_currency": "USD",
                    "amount": 1000,
                    "cntr_amount": 802.54,
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
        self.assertEqual(len(resp['cashflows']), 2)
        self.assertEqual(resp['recurring'], False)
        self.assertEqual(resp['installment'], True)

        prev_payment = resp.copy()

        # Test update payment endpoint
        payload['installments'] = [
            {
                "cashflow_id": prev_payment['cashflows'][0]['cashflow_id'],
                "date": str(now.date()),
                "sell_currency": "GBP",
                "buy_currency": "USD",
                "amount": 250,
                "cntr_amount":200.64,
                "lock_side": "USD"
            },
            {
                "cashflow_id": prev_payment['cashflows'][1]['cashflow_id'],
                "date": str(date1.date()),
                "sell_currency": "GBP",
                "buy_currency": "USD",
                "amount": 750,
                "cntr_amount": 601.93,
                "lock_side": "USD"
            },
            {
                "date": str(date2.date()),
                "sell_currency": "GBP",
                "buy_currency": "USD",
                "amount": 500,
                "cntr_amount": 401.27,
                "lock_side": "USD"
            }
        ]
        resp, status_code = self.do_api_call(
            method='PUT',
            url=reverse(RET_UPD_DEL_NAME, kwargs={'pk': resp['id']}),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['cashflows']), 3)

        # Get first created payments
        resp.pop('approvers')
        resp.pop('min_approvers')
        resp.pop('assigned_approvers')
        created_payment = resp.copy()

        # Test retrieve payment endpoint
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(RET_UPD_DEL_NAME, kwargs={'pk': created_payment['id']})
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        resp.pop('approvers')
        resp.pop('min_approvers')
        resp.pop('assigned_approvers')
        self.assertEqual(resp, created_payment)

        # Test delete payment endpoint
        resp, status_code = self.do_api_call(
            method='DELETE',
            url=reverse(RET_UPD_DEL_NAME, kwargs={'pk': created_payment['id']})
        )
        self.assertEqual(status_code, status.HTTP_204_NO_CONTENT)

