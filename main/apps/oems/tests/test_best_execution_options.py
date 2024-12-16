from datetime import datetime, timedelta
from django.urls import reverse
from rest_framework import status
from main.apps.oems.api.dataclasses.liquidity_insight import LiquidityStatus

from main.apps.payment.models.payment import ExecutionOptions, Payment
from main.apps.payment.tests.base_payment_api_test import BasePaymentAPITest

from unittest import mock

from main.apps.settlement.models import Beneficiary

LIST_CREATE_NAME = 'main:payment:payment-cashflow'
EXECUTION_TIMING_NAME = 'main:oems:best-execution-timings'


class BestExecutionOptionsApiTest(BasePaymentAPITest):
    def setUp(self) -> None:
        super().setUp()
        self.date = datetime.now()
        self.payload = {
            "amount": 100,
            "buy_currency": "EUR",
            "delivery_date": str(self.date.date()),
            "destination_account_id": "1234",
            "fee_in_bps": 0,
            "fee": 0,
            "lock_side": "EUR",
            "name": "USDEUR OneTime Payment",
            "origin_account_id": "4321",
            "purpose_of_payment": Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS.value,
            "sell_currency": "USD"
        }
        self.fwd_date = self.date + timedelta(days=3)

    def tearDown(self) -> None:
        return super().tearDown()

    def get_forward_payload(self, sell_ccy:str='USD', buy_ccy:str='EUR') -> dict:
        payload = self.payload.copy()
        payload['sell_currency'] = sell_ccy
        payload['buy_currency'] = buy_ccy
        payload['lock_side'] = buy_ccy
        payload['name'] = f'{sell_ccy}{buy_ccy} OneTime FWD Payment'
        payload['delivery_date'] = str(self.fwd_date.date())
        return payload

    def get_recurring_payload(self) -> dict:
        now = self.date
        end_date = now + timedelta(days=21)

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
        return payload

    def get_installment_payload(self) -> dict:
        now = self.date
        date1 = now + timedelta(days=7)

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
        return payload

    def mock_get_bestx_status(self, recommend:bool = True, session:str='London') -> dict:
        return {
            'market': 'USDEUR',
            'recommend': recommend,
            'session': session,
            'check_back': None,
            'execute_before': datetime.now() + timedelta(minutes=1),
            'unsupported': False
        }

    def mock_fx_spot_info(self) -> dict:
        return {
            'spot_value_date': self.date.date(),
            'settlement_days': 1,
            'days': 1
        }

    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_good_open_spot(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                            mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                            mock_get_fx_spot_info, mock_session, mock_next_session):
        """Good/Open/Spot"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'London'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = LiquidityStatus.GOOD.value
        mock_best_exec_stat.return_value = self.mock_get_bestx_status()
        mock_weekend.return_value = False
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.IMMEDIATE_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.GOOD.value)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.GOOD.value)


    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_not_good_open_spot(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """NotGood/Open/Spot"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'London'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = LiquidityStatus.ACCEPTABLE.value
        mock_best_exec_stat.return_value = self.mock_get_bestx_status()
        mock_weekend.return_value = False
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.IMMEDIATE_SPOT in option_values)
        self.assertTrue(ExecutionOptions.STRATEGIC_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.ACCEPTABLE.value)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.ACCEPTABLE.value)


    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_good_open_fwd_api(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """Good/Open/FwdApi"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'London'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = LiquidityStatus.GOOD.value
        mock_best_exec_stat.return_value = self.mock_get_bestx_status()
        mock_weekend.return_value = False
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.get_forward_payload()
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.IMMEDIATE_FORWARD in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.GOOD.value)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_FORWARD in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.GOOD.value)


    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_not_good_open_fwd_api(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """NotGood/Open/FwdApi"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'London'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = LiquidityStatus.ACCEPTABLE.value
        mock_best_exec_stat.return_value = self.mock_get_bestx_status()
        mock_weekend.return_value = False
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.get_forward_payload()
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 3)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.IMMEDIATE_FORWARD in option_values)
        self.assertTrue(ExecutionOptions.STRATEGIC_FORWARD in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.ACCEPTABLE.value)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_FORWARD in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.ACCEPTABLE.value)


    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_good_open_fwd_manual(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """Good/Open/FwdManual"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'London'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = LiquidityStatus.GOOD.value
        mock_best_exec_stat.return_value = self.mock_get_bestx_status()
        mock_weekend.return_value = False
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.get_forward_payload(buy_ccy='PHP')
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.IMMEDIATE_NDF in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.GOOD.value)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_NDF in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.GOOD.value)


    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_not_good_open_fwd_manual(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """NotGood/Open/FwdManual"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'London'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = LiquidityStatus.ACCEPTABLE.value
        mock_best_exec_stat.return_value = self.mock_get_bestx_status()
        mock_weekend.return_value = False
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.get_forward_payload(buy_ccy='PHP')
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 3)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.IMMEDIATE_NDF in option_values)
        self.assertTrue(ExecutionOptions.STRATEGIC_NDF in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.ACCEPTABLE.value)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_NDF in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.ACCEPTABLE.value)


    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_fwd_unsupported(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """FwdUnsupported"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'London'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = LiquidityStatus.GOOD.value
        mock_best_exec_stat.return_value = self.mock_get_bestx_status()
        mock_weekend.return_value = False
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.get_forward_payload(buy_ccy='XOF')
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.GOOD.value)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        mock_liquidity.return_value = LiquidityStatus.ACCEPTABLE.value
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.ACCEPTABLE.value)

    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_recurring_installment(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """Recurring/Installment"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'London'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = LiquidityStatus.GOOD.value
        mock_best_exec_stat.return_value = self.mock_get_bestx_status()
        mock_weekend.return_value = False
        mock_req_approval.return_value = False

        # Test execution timing endpoint for recurring payment
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.get_recurring_payload()
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.GOOD.value)

        # Test execution timing endpoint for installment payment
        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.get_installment_payload()
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == LiquidityStatus.GOOD.value)


    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_none_close_fwd_api(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """None/Close/FwdApi"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'Weekend'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = None
        mock_best_exec_stat.return_value = self.mock_get_bestx_status(session='Weekend')
        mock_weekend.return_value = True
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.get_forward_payload()
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_FORWARD in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == None)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        mock_best_exec_stat.return_value = self.mock_get_bestx_status(recommend=False, session='Weekend')

        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_FORWARD in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == None)


    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_none_close_fwd_manual(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """None/Close/FwdManual"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'Weekend'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = None
        mock_best_exec_stat.return_value = self.mock_get_bestx_status(session='Weekend')
        mock_weekend.return_value = True
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.get_forward_payload(buy_ccy='PHP')
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_NDF in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == None)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        mock_best_exec_stat.return_value = self.mock_get_bestx_status(recommend=False, session='Weekend')

        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 2)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_NDF in option_values)
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == None)


    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_none_close_fwd_unsupported(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """None/Close/FwdUnsupported"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'Weekend'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = None
        mock_best_exec_stat.return_value = self.mock_get_bestx_status(session='Weekend')
        mock_weekend.return_value = True
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.get_forward_payload(buy_ccy='XOF')
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == None)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        mock_best_exec_stat.return_value = self.mock_get_bestx_status(recommend=False, session='Weekend')

        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.SCHEDULED_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == None)


    @mock.patch('main.apps.oems.backend.exec_utils.get_current_or_next_mkt_session')
    @mock.patch('main.apps.oems.backend.exec_utils.get_trading_session')
    @mock.patch('main.apps.oems.services.se.execution_option.get_fx_spot_info')
    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @mock.patch('main.apps.oems.validators.ticket.get_reference_data')
    @mock.patch('main.apps.oems.validators.ticket.shared_ticket_bene_validation')
    @mock.patch('main.apps.marketdata.services.spread.SpreadProvider.get_liquidity_status')
    @mock.patch('main.apps.oems.services.se.execution_option.get_best_execution_status')
    @mock.patch('main.apps.oems.services.se.execution_option.ExecutionOptionProvider._is_weekend')
    @mock.patch('main.apps.approval.services.approval.CompanyApprovalService.is_transaction_require_approval')
    def test_none_close_spot(self, mock_req_approval, mock_weekend, mock_best_exec_stat, mock_liquidity,
                                mock_bene_validation,mock_get_ref_data, mock_get_exec_config,
                                mock_get_fx_spot_info, mock_session, mock_next_session):
        """None/Close/Spot"""
        mock_get_fx_spot_info.return_value = self.mock_fx_spot_info()
        mock_session.return_value = 'Weekend'
        mock_next_session.return_value = True, {"gmtt_close": self.date, 'gmtt_open': self.date}
        mock_get_ref_data.return_value = self.mock_ref_data
        mock_get_exec_config.return_value = self.mock_get_exec_config_eurusd_reponse
        mock_bene_validation.return_value = True
        mock_liquidity.return_value = None
        mock_best_exec_stat.return_value = self.mock_get_bestx_status(session='Weekend')
        mock_weekend.return_value = True
        mock_req_approval.return_value = False

        resp, status_code = self.do_api_call(
            method='POST',
            url=reverse(LIST_CREATE_NAME),
            payload=self.payload
        )
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        payment = resp.copy()

        # Test execution timing endpoint for approval_required = False
        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == None)

        # Test execution timing endpoint for approval_required = True
        mock_req_approval.return_value = True
        mock_best_exec_stat.return_value = self.mock_get_bestx_status(recommend=False, session='Weekend')

        resp, status_code = self.do_api_call(
            method='GET',
            url=reverse(EXECUTION_TIMING_NAME, kwargs={'payment_id': payment['id']})
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp['execution_timings']), 1)

        option_values = [timing['value'] for timing in resp['execution_timings']]
        self.assertTrue(ExecutionOptions.STRATEGIC_SPOT in option_values)

        exec_data = resp['execution_data']
        self.assertTrue(exec_data['liquidity_insight']['liquidity'] == None)
