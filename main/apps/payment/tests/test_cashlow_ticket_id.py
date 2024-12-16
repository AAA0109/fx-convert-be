from datetime import datetime
from django.urls import reverse
from django.db.models import signals
from rest_framework import status

from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.oems.models.ticket import Ticket
from main.apps.payment.models.payment import ExecutionOptions, Payment
from main.apps.payment.services.converter import PaymentToTicketConverter
from main.apps.payment.tests.base_payment_api_test import BasePaymentAPITest

from unittest import mock

from main.apps.settlement.models import Beneficiary

LIST_CREATE_NAME = 'main:payment:payment-cashflow'


class TestCashflowTicketID(BasePaymentAPITest):

    def setUp(self) -> None:
        super().setUp()
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

        self.quote = quote = {
            'rate': {
                'value': 1.1164,
                'lock_side': 'Settlement',
                'rate_type': 'EURUSD',
                'operation': 'Multiply'
            },
            'quote_id': 'f2975afbe98e4ebd9fc3342e992f0640',
            'payment': {
                'currency': 'EUR',
                'amount': 716.59,
                'amount_domestic': 767.7
            },
            'settlement': {
                'currency': 'USD',
                'amount': 800.0,
                'amount_domestic': 800.0
            },
            'cost_in_bps': 100
        }


    def tearDown(self) -> None:
        return super().tearDown()

    @mock.patch('main.apps.oems.backend.api.pangea_client.corpay_spot_rfq')
    @mock.patch('main.apps.oems.backend.api.pangea_client.corpay_fwd_rfq')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.oems.validators.ticket.validate_instrument_amount')
    @mock.patch('main.apps.oems.validators.ticket.pangea_client.get_exec_config')
    @mock.patch('main.apps.approval.services.limit.CompanyLimitService.convert_to_company_currency')
    def test_cashflow_ticket_id_signal_celery_task(self, mock_conv_amnt, mock_get_exec_config2, mock_valid_amount,
                                                   mock_bene_validation, mock_get_ref_data, mock_get_exec_config,
                                                   mock_corpay_fwd_rfq, mock_corpay_spot_rfq):
        from main.apps.payment.tasks.update_cashflow_ticket_id import update_cashflow_ticket_id_task

        mock_conv_amnt.return_value = self.mock_convert_amount
        data = []

        def post_save_handler(signal, sender, instance:Ticket, **kwargs):
            if sender == Ticket:
                data.append(
                    (instance, sender, kwargs.get("created"), kwargs.get("raw", False))
                )
                update_cashflow_ticket_id_task(ticket_id=str(instance.ticket_id), cashflow_id=str(instance.cashflow_id))

        signals.post_save.connect(post_save_handler, weak=False)

        try:
            mock_bene_validation.return_value = True
            mock_corpay_spot_rfq.return_value = self.quote
            mock_corpay_fwd_rfq.return_value = self.quote
            mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
            mock_get_exec_config2.return_value = self.mock_get_exec_config_eurusd_reponse
            mock_get_ref_data.return_value = self.mock_ref_data
            mock_valid_amount.return_value = None

            now = datetime.now()

            payload = {
                "amount": 100,
                "buy_currency": "EUR",
                "delivery_date": str(now.date()),
                "destination_account_id": "1234",
                "destination_account_method": "swift",
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

            payment = Payment.objects.get(pk=resp['id'])
            converter = PaymentToTicketConverter(payment=payment)
            tickets, errors = converter.convert_to_tickets()
            ticket = tickets[0]
            cashflow = SingleCashFlow.objects.get(cashflow_id=ticket.cashflow_id)

            self.assertEqual(data, [
                (ticket, Ticket, True, False)
            ])
            # Test if ticket and cashflow id on the related cashflow are equal
            self.assertEqual(cashflow.ticket_id, ticket.ticket_id)
            self.assertEqual(cashflow.cashflow_id, ticket.cashflow_id)
        finally:
            data[:] = []
            signals.post_save.disconnect(post_save_handler)

