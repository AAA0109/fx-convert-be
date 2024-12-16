from datetime import datetime, timedelta
from django.urls import reverse
from rest_framework import status

from main.apps.payment.models.payment import ExecutionOptions, Payment
from main.apps.payment.tests.base_payment_api_test import BasePaymentAPITest
from unittest import mock

from main.apps.settlement.models import Beneficiary


class TestRecurringPaymentAPI(BasePaymentAPITest):

    def setUp(self) -> None:
        super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.approval.services.limit.CompanyLimitService.convert_to_company_currency')
    def test_recurring_payment_api(self, mock_conv_amnt, mock_bene_validation, mock_get_ref_data, mock_get_exec_config):
        LIST_CREATE_NAME = 'main:payment:payment-cashflow'
        RET_UPD_DEL_NAME = 'main:payment:payment-cashflow-with-pk'
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_conv_amnt.return_value = self.mock_convert_amount

        now = datetime.now()
        end_date = now + timedelta(days=21)
        end_date2 = now + timedelta(days=5*30)

        payload = {
            "amount": 100,
            "buy_currency": "EUR",
            "destination_account_id": "1234",
            "fee_in_bps": 20,
            "fee": 0.2,
            "lock_side": "EUR",
            "name": "USDEUR Recurring Payment",
            "origin_account_id": "4321",
            "purpose_of_payment": Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS.value,
            "sell_currency": "USD",
            "execution_timing": ExecutionOptions.IMMEDIATE_SPOT.value,
            "periodicity": f"DTSTART:{now.strftime('%Y%m%dT%H%M%SZ')}\nRRULE:FREQ=WEEKLY;\
                INTERVAL=1;UNTIL={end_date.strftime('%Y%m%dT%H%M%SZ')}",
            "periodicity_start_date": str(now.date()),
            "periodicity_end_date": str(end_date.date())
        }

        # Test create payment endpoint
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp['recurring'], True)
        self.assertEqual(resp['installment'], False)

        # Test update payment endpoint
        payload['periodicity'] = f"DTSTART:{now.strftime('%Y%m%dT%H%M%SZ')}\nRRULE:FREQ=MONTHLY;\
            INTERVAL=1;UNTIL={end_date2.strftime('%Y%m%dT%H%M%SZ')}"
        payload['periodicity_start_date'] = str(now.date())
        payload['periodicity_end_date'] = str(end_date2.date())
        resp, status_code = self.do_api_call(
            method='PUT',
            url=reverse(RET_UPD_DEL_NAME, kwargs={'pk': resp['id']}),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_200_OK)

        # Get first created payments
        created_payment = resp.copy()

        # Test retrieve payment endpoint
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(RET_UPD_DEL_NAME, kwargs={'pk': created_payment['id']})
        )
        self.assertEqual(status_code, status.HTTP_200_OK)

        # Test delete payment endpoint
        resp, status_code = self.do_api_call(
            method='DELETE',
            url=reverse(RET_UPD_DEL_NAME, kwargs={'pk': created_payment['id']})
        )
        self.assertEqual(status_code, status.HTTP_204_NO_CONTENT)

