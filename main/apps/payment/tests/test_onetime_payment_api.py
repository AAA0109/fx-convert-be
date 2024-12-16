from datetime import datetime, timedelta
from unittest import mock
from django.urls import reverse
from rest_framework import status

from main.apps.payment.models.payment import ExecutionOptions, Payment
from main.apps.payment.tests.base_payment_api_test import BasePaymentAPITest
from main.apps.settlement.models import Beneficiary


class TestOneTimePaymentAPI(BasePaymentAPITest):

    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.approval.services.limit.CompanyLimitService.convert_to_company_currency')
    def test_one_time_payment_api(self, mock_conv_amnt, mock_bene_validation, mock_get_ref_data, mock_get_exec_config):
        LIST_CREATE_NAME = 'main:payment:payment-cashflow'
        RET_UPD_DEL_NAME = 'main:payment:payment-cashflow-with-pk'
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_conv_amnt.return_value = self.mock_convert_amount

        now = datetime.now()

        payload = {
            "amount": 100,
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
            "execution_timing": ExecutionOptions.IMMEDIATE_SPOT.value
        }

        # Test create payment endpoint
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp['cashflows']), 1)
        self.assertEqual(resp['recurring'], False)
        self.assertEqual(resp['installment'], False)

        # Test update payment endpoint
        payload['amount'] = 200
        payload['fee_in_bps'] = 50
        payload['fee'] = 1
        resp, status_code = self.do_api_call(
            method='PUT',
            url=reverse(RET_UPD_DEL_NAME, kwargs={'pk': resp['id']}),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(resp['amount'], 200)
        self.assertEqual(resp['fee_in_bps'], 50)
        self.assertEqual(resp['fee'], 1)

        # Get first created payments
        resp.pop('approvers')
        resp.pop('min_approvers')
        resp.pop('assigned_approvers')
        created_payment = resp.copy()

        # Create multiple payments
        for i in range(10):
            new_date = now + timedelta(days=1 if i == 0 else i*1)
            payload['delivery_date'] = str(new_date.date())
            resp, status_code = self.do_api_call(
                method='POST',
                url=reverse(LIST_CREATE_NAME),
                payload=payload
            )

        # Test list payments endpoint
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(LIST_CREATE_NAME)
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['results']), 11)
        resp_10:dict = resp['results'][10]
        resp_10.pop('approvers')
        resp_10.pop('min_approvers')
        resp_10.pop('assigned_approvers')
        self.assertEqual(resp_10, created_payment)

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
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(LIST_CREATE_NAME)
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['results']), 10)

