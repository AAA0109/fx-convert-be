from datetime import datetime, timedelta
from unittest import mock
from django.urls import reverse
from rest_framework import status

from main.apps.payment.models.payment import ExecutionOptions, Payment
from main.apps.payment.tests.base_payment_api_test import BasePaymentAPITest
from main.apps.settlement.models import Beneficiary

LIST_CREATE_NAME = 'main:payment:payment-cashflow'
INSTALLMENT_URL_NAME = 'main:payment:payment-cashflows'
INSTALLMENT_WITH_PK_URL_NAME = 'main:payment:payment-cashflows-with-pk'


class TestCashflowAPI(BasePaymentAPITest):
    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.approval.services.limit.CompanyLimitService.convert_to_company_currency')
    def test_installment_cashflow_api(self, mock_conv_amnt, mock_bene_validation, mock_get_ref_data, mock_get_exec_config):
        now = datetime.now()
        date1 = now + timedelta(days=7)
        date2 = now + timedelta(days=14)
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_conv_amnt.return_value = self.mock_convert_amount

        payload = {
            "buy_currency": "USD",
            "destination_account_id": "1234",
            "destination_account_method": "swift",
            "lock_side": "USD",
            "name": "GBPUSD Installment Payment",
            "origin_account_id": "4321",
            "origin_account_method": "swift",
            "purpose_of_payment": Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS.value,
            "sell_currency": "GBP",
            "execution_timing": ExecutionOptions.IMMEDIATE_SPOT.value,
            "installments": [
                {
                    "date": str(now.date()),
                    "sell_currency": "GBP",
                    "buy_currency": "USD",
                    "amount": 500,
                    "cntr_amount": 401.28,
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

        # Create cashflow payment
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED, resp)
        payment = resp.copy()

        new_installment_payload = {
            "sell_currency": "GBP",
            "buy_currency": "USD",
            "lock_side": "USD",
            "pay_date": str(date2),
            "amount": 100,
            "cntr_amount": 80.27
        }

        # Test create cashflow endpoint
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(INSTALLMENT_URL_NAME, kwargs={'payment_id': payment['id']}),
            payload=new_installment_payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        installment = resp.copy()

        # Test list cashflow endpoint
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(INSTALLMENT_URL_NAME, kwargs={'payment_id': payment['id']})
        )
        self.assertEqual(status_code, status.HTTP_200_OK)

        # Test retrieve cashflow endpoint
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(INSTALLMENT_WITH_PK_URL_NAME, kwargs={'payment_id': payment['id'], 'cashflow_id': installment['cashflow_id']})
        )
        self.assertEqual(status_code, status.HTTP_200_OK)

        # Test update cashflow endpoint
        new_installment_payload['amount'] = 150
        new_installment_payload['pay_date'] = date2.strftime('%Y-%m-%dT%H:%M:%SZ')
        resp, status_code = self.do_api_call(
            method='PUT',
            url=reverse(INSTALLMENT_WITH_PK_URL_NAME, kwargs={'payment_id': payment['id'], 'cashflow_id': installment['cashflow_id']}),
            payload=new_installment_payload
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(resp['amount'], new_installment_payload['amount'])
        self.assertEqual(resp['pay_date'], new_installment_payload['pay_date'])

         # Test delete cashflow endpoint
        resp, status_code = self.do_api_call(
            method='DELETE',
            url=reverse(INSTALLMENT_WITH_PK_URL_NAME, kwargs={'payment_id': payment['id'], 'cashflow_id': installment['cashflow_id']})
        )
        self.assertEqual(status_code, status.HTTP_204_NO_CONTENT)
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(INSTALLMENT_URL_NAME, kwargs={'payment_id': payment['id']})
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp), 2)

    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.approval.services.limit.CompanyLimitService.convert_to_company_currency')
    def test_recurring_cashflow_api(self, mock_conv_amnt, mock_bene_validation, mock_get_ref_data, mock_get_exec_config):
        now = datetime.now()
        end_date = now + timedelta(days=21)
        end_date2 = now + timedelta(days=14)

        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_conv_amnt.return_value = self.mock_convert_amount

        payload = {
            "amount": 100,
            "cntr_amount": 80.27,
            "buy_currency": "USD",
            "destination_account_id": "1234",
            "lock_side": "USD",
            "name": "GBPUSD Installment Payment",
            "origin_account_id": "4321",
            "purpose_of_payment": Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS.value,
            "sell_currency": "GBP",
            "execution_timing": ExecutionOptions.IMMEDIATE_SPOT.value,
            "periodicity": f"DTSTART:{now.strftime('%Y%m%dT%H%M%SZ')}\nRRULE:FREQ=WEEKLY;\
                INTERVAL=1;WKST=MO;BYDAY=MO;UNTIL={end_date.strftime('%Y%m%dT%H%M%SZ')}",
            "periodicity_start_date": str(now.date()),
            "periodicity_end_date": str(end_date.date())
        }

        # Create cashflow payment
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        new_installment_payload = {
            "sell_currency": "GBP",
            "buy_currency": "USD",
            "lock_side": "USD",
            "pay_date": end_date2.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "amount": 100,
            "cntr_amount": 80.27
        }

        # Test create cashflow endpoint
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(INSTALLMENT_URL_NAME, kwargs={'payment_id': payment['id']}),
            payload=new_installment_payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        installment = resp.copy()

        # Test list cashflow endpoint
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(INSTALLMENT_URL_NAME, kwargs={'payment_id': payment['id']})
        )
        self.assertEqual(status_code, status.HTTP_200_OK)

        # Test retrieve cashflow endpoint
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(INSTALLMENT_WITH_PK_URL_NAME, kwargs={'payment_id': payment['id'], 'cashflow_id': installment['cashflow_id']})
        )
        self.assertEqual(status_code, status.HTTP_200_OK)

        # Test update cashflow endpoint
        new_installment_payload['amount'] = 150
        new_installment_payload['pay_date'] = end_date2.strftime('%Y-%m-%dT%H:%M:%SZ')
        resp, status_code = self.do_api_call(
            method='PUT',
            url=reverse(INSTALLMENT_WITH_PK_URL_NAME, kwargs={'payment_id': payment['id'], 'cashflow_id': installment['cashflow_id']}),
            payload=new_installment_payload
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(resp['amount'], new_installment_payload['amount'])
        self.assertEqual(resp['pay_date'], new_installment_payload['pay_date'])

         # Test delete cashflow endpoint
        resp, status_code = self.do_api_call(
            method='DELETE',
            url=reverse(INSTALLMENT_WITH_PK_URL_NAME, kwargs={'payment_id': payment['id'], 'cashflow_id': installment['cashflow_id']})
        )
        self.assertEqual(status_code, status.HTTP_204_NO_CONTENT)
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(INSTALLMENT_URL_NAME, kwargs={'payment_id': payment['id']})
        )
        self.assertEqual(status_code, status.HTTP_200_OK)

