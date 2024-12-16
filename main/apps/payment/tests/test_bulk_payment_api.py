from datetime import datetime, timedelta
from unittest import mock
import uuid
from django.urls import reverse
from rest_framework import status

from main.apps.settlement.models import Beneficiary
from main.apps.payment.models.payment import Payment
from main.apps.payment.tests.base_payment_api_test import BasePaymentAPITest


class TestBulkPaymentAPI(BasePaymentAPITest):

    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.approval.services.limit.CompanyLimitService.convert_to_company_currency')
    def test_bulk_payment_api(self, mock_conv_amnt, mock_bene_validation, mock_get_ref_data, mock_get_exec_config):
        BULK_PAYMENT_NAME = 'main:payment:bulk-payment-cashflow'
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_conv_amnt.return_value = self.mock_convert_amount

        now = datetime.now()

        payload = {
            'payments': []
        }

        origin_account_id = uuid.uuid4().__str__()
        destination_account_id = uuid.uuid4().__str__()

        n_bulk = 30
        for i in range(n_bulk):
            factor = i+1
            payload['payments'].append(
                {
                    "amount": 10*factor,
                    "buy_currency": "EUR",
                    "value_date": str(now.date() + timedelta(days=factor)),
                    "destination": destination_account_id,
                    "lock_side": "EUR",
                    "description": f"USDEUR Payment {factor}",
                    "origin": origin_account_id,
                    "purpose_of_payment": Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS.value,
                    "sell_currency": "USD"
                }
            )

        # Test create bulk payment endpoint
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(BULK_PAYMENT_NAME),
            payload=payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp['payments']), n_bulk)

        payments = resp['payments']
        payment_group = resp['payments'][0]['payment_group']

        n_new_bulk = 5

        # Populate payload to add multiple new payment
        added_payments = []
        for i in range(n_new_bulk):
            factor = i+1
            added_payments.append(
                {
                    "amount": 10*factor,
                    "buy_currency": "EUR",
                    "value_date": str(now.date() + timedelta(days=factor)),
                    "destination": destination_account_id,
                    "lock_side": "EUR",
                    "description": f"USDEUR Payment new_{factor}",
                    "origin": origin_account_id,
                    "purpose_of_payment": Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS.value,
                    "sell_currency": "USD"
                }
            )

        # Populate payload to update multiple existing payment
        updated_payments = []
        for i in range(0, 20):
            if i % 2 == 1:
                payment = payments[i]
                factor = i+1
                updated_payments.append(
                    {
                        "payment_id": payment['payment_id'],
                        "amount": payment['amount'] + 3*factor \
                             if i > 10 else payment['amount'],
                        "buy_currency": payment['sell_currency'],
                        "value_date": str(now.date() + timedelta(days=factor + 2)),
                        "destination": payment['origin_account_id'].replace('USDEUR', 'EURUSD'),
                        "lock_side": payment['sell_currency'],
                        "description": payment['name'],
                        "origin": payment['destination_account_id'],
                        "purpose_of_payment": Beneficiary.Purpose.PERSONNEL_PAYMENT.label + '_updated',
                        "sell_currency": payment['buy_currency'],
                    }
                )

        # Populate multiple payment ids to delete
        deleted_payments = []
        for i in range(20, 30):
            deleted_payments.append(payments[i]['payment_id'])

        update_payload = {
            'payment_group': payment_group,
            'added_payments': added_payments,
            'updated_payments': updated_payments,
            'deleted_payments': deleted_payments,
        }

        # Test update bulk payment endpoint
        resp, status_code = self.do_api_call(
            method='PUT',
            url=reverse(BULK_PAYMENT_NAME),
            payload=update_payload
        )
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['payments']), 25)
        
