import unittest

from typing import List
from unittest import mock
from hdlib.DateTime.Date import Date
from django.db.models.signals import post_save
from django.test import TestCase
from django.conf import settings

from main.apps.account.models.account import Account
from main.apps.account.models.autopilot_data import AutopilotData
from main.apps.account.models.cashflow import CashFlow
from main.apps.account.models.company import Company
from main.apps.broker.models.broker import BrokerAccount
from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition
from main.apps.hedge.services.forward_to_ticket import ForwardToTicketFactory
from main.apps.hedge.services.hard_limits import AutopilotHardLimitProvider
from main.apps.oems.models.ticket import Ticket
from main.apps.billing.signals.handlers import create_stripe_customer_id_for_company
from main.apps.strategy.models.choices import Strategies


class ForwardToTicketTest(TestCase):

    def setUp(self) -> None:
        post_save.disconnect(receiver=create_stripe_customer_id_for_company, sender=Company)

        _, self.usd = Currency.create_currency(symbol="$", mnemonic="USD", name="US Dollar")
        _, self.euro = Currency.create_currency(symbol="€", mnemonic="EUR", name="EURO")

        self.__create_pairs(currs=[self.usd, self.euro])

        self.company = Company(name="TESTCOMPANY1", currency=self.usd)
        self.company.save()

        self.account1 = Account.create_account(name="ACCOUNT1", company=self.company)

        self.usdusd_cny = {
            "id": 620,
            "market": "USDUSD",
            "subaccounts": [
                "DU6108530"
            ],
            "staging": False,
            "default_broker": "CORPAY",
            "default_exec_strat": "MARKET",
            "default_hedge_strat": "SELFDIRECTED",
            "default_algo": "LIQUID_TWAP1",
            "rfq_type": "unsupported",
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
            "company": 13
        }

    def tearDown(self) -> None:
        Ticket.objects.all().delete()
        AutopilotData.objects.all().delete()
        DraftFxForwardPosition.objects.all().delete()
        CashFlow.objects.all().delete()
        post_save.connect(receiver=create_stripe_customer_id_for_company, sender=Company)

    def __create_pairs(self, currs: List[Currency]):
        pairs = []
        for curr1 in currs:
            for curr2 in currs:
                _, pair = FxPair.create_fxpair(base=curr1, quote=curr2)
                pairs.append(pair)
        return pairs

    def __create_autopilotdata(self, account: Account, upper_limit: float, lower_limit: float) -> AutopilotData:
        autopilot_data = AutopilotData(
            account=account,
            upper_limit=upper_limit,
            lower_limit=lower_limit
        )
        autopilot_data.save()
        return autopilot_data

    def __create_cashflow(self):
        date = Date.utcnow() + 7

        cashflow = CashFlow.create_cashflow(
            account=self.account1,
            amount=100,
            currency=self.usd,
            date=date,
            name="cf1", status=CashFlow.CashflowStatus.PENDING_ACTIVATION)
        cashflow.save()
        return cashflow

    def __create_draft_fx_fwd_position(self, cashflow: CashFlow, fx_fwd_price: float,
                                       risk_reduction: float = 1) -> DraftFxForwardPosition:
        fwd = DraftFxForwardPosition(
            status=DraftFxForwardPosition.Status.PENDING_ACTIVATION,
            risk_reduction=risk_reduction,
            is_cash_settle=False,
            estimated_fx_forward_price=fx_fwd_price,
            company=self.company,
            cashflow=cashflow
        )
        fwd.save()
        return fwd

    @unittest.skipIf(not settings.OEMS_RUN_TESTS, "Only run if OEMS_RUN_TESTS is set to True")
    def test_autopilot_hard_limits(self):
        autopilot_data = self.__create_autopilotdata(account=self.account1, upper_limit=5/100, lower_limit=-3/100)
        cashflow = self.__create_cashflow()
        draft_fwd_pos = self.__create_draft_fx_fwd_position(cashflow=cashflow, fx_fwd_price=1.0)

        # Non-padded hard limits
        autopilot_limits_non_padded = AutopilotHardLimitProvider(draft_fwd_position=draft_fwd_pos)
        non_padded_limits = autopilot_limits_non_padded.calculate_hard_limit()

        self.assertEqual(non_padded_limits.upper_target, 1.05)
        self.assertEqual(non_padded_limits.lower_target, 0.97)

        # Padded hard limits
        autopilot_limits_padded = AutopilotHardLimitProvider(draft_fwd_position=draft_fwd_pos, padding_limit=0.5/100)
        padded_limits = autopilot_limits_padded.calculate_hard_limit()

        self.assertEqual(padded_limits.upper_target, 1.055)
        self.assertEqual(padded_limits.lower_target, 0.975)

    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @unittest.skipIf(not settings.OEMS_RUN_TESTS, "Only run if OEMS_RUN_TESTS is set to True")
    def test_autopilot_forward_to_ticket_risk_red_100(self, mock_get_exec_config):
        mock_get_exec_config.return_value = self.usdusd_cny

        autopilot_data = self.__create_autopilotdata(account=self.account1, upper_limit=5/100, lower_limit=-3/100)
        cashflow = self.__create_cashflow()
        draft_fwd_pos = self.__create_draft_fx_fwd_position(cashflow=cashflow, fx_fwd_price=1.0)

        tickets = ForwardToTicketFactory().convert_forward_to_ticket(draft_fwd_position=draft_fwd_pos, strategy=Strategies.AUTOPILOT.value)

        self.assertIsNotNone(tickets)
        self.assertEqual(len(tickets), 1)

        ticket_with_no_limits = tickets[0]

        self.assertIsNone(ticket_with_no_limits.upper_trigger)
        self.assertIsNone(ticket_with_no_limits.lower_trigger)

    @mock.patch('main.apps.oems.backend.api.pangea_client.get_exec_config')
    @unittest.skipIf(not settings.OEMS_RUN_TESTS, "Only run if OEMS_RUN_TESTS is set to True")
    def test_autopilot_forward_to_ticket_risk_red_less100(self, mock_get_exec_config):
        mock_get_exec_config.return_value = self.usdusd_cny

        autopilot_data = self.__create_autopilotdata(account=self.account1, upper_limit=5/100, lower_limit=-3/100)
        cashflow = self.__create_cashflow()
        draft_fwd_pos = self.__create_draft_fx_fwd_position(cashflow=cashflow, fx_fwd_price=1.0, risk_reduction=50/100)

        tickets = ForwardToTicketFactory().convert_forward_to_ticket(draft_fwd_position=draft_fwd_pos, strategy=Strategies.AUTOPILOT.value)

        self.assertIsNotNone(tickets)
        self.assertEqual(len(tickets), 2)

        ticket_with_limits = tickets[0]
        ticket_with_no_limits = tickets[1]

        self.assertEqual(ticket_with_limits.upper_trigger, 1.05)
        self.assertEqual(ticket_with_limits.lower_trigger, 0.97)

        self.assertIsNone(ticket_with_no_limits.upper_trigger)
        self.assertIsNone(ticket_with_no_limits.lower_trigger)
