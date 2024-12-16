import unittest

from django.test import TestCase
from hdlib.Core.Currency import EUR, USD

from hdlib.Core.FxPair import FxPair
from hdlib.DateTime.Date import Date
from main.apps.account.models import Company
from main.apps.currency.models import Currency
from main.apps.hedge.models import CompanyHedgeAction

from main.apps.oems.support.tickets import OMSOrderTicket


class OMSOrderTicketTest(TestCase):
    def test_to_string(self):
        # noinspection DuplicatedCode
        _, usd = Currency.create_currency('USD', 'USD', 'USD')

        test_company = Company.objects.create(name='Test Company 1', currency=usd, status=Company.CompanyStatus.ACTIVE)
        _, action = CompanyHedgeAction.add_company_hedge_action(company=test_company, time=Date.create(ymd=2020_01_01))

        fxpair = FxPair(base=EUR, quote=USD)
        ticket = OMSOrderTicket(amount_filled=10000,
                                fx_pair=fxpair,
                                amount_remaining=100,
                                average_price=1.23,
                                commission=1.0,
                                cntr_commission=0.5,
                                company_hedge_action=action,
                                state=OMSOrderTicket.States.STAGED)

        ticket_string = str(ticket)
        self.assertEqual(ticket_string,
                         f"{{"
                         f"fxpair: EUR/USD, "
                         f"company_hedge_action_id: {action.id}, "
                         f"amount_filled: 10000, "
                         f"average_price: 1.23, "
                         f"commission: 1.0, "
                         f"cntr_commission: 0.5, "
                         f"state: States.STAGED"
                         f"}}")

    def test_sanity(self):
        # noinspection DuplicatedCode
        _, usd = Currency.create_currency('USD', 'USD', 'USD')

        test_company = Company.objects.create(name='Test Company 1', currency=usd, status=Company.CompanyStatus.ACTIVE)
        _, action = CompanyHedgeAction.add_company_hedge_action(company=test_company, time=Date.create(ymd=20200101))

        fxpair = FxPair(base=EUR, quote=USD)
        ticket = OMSOrderTicket(amount_filled=10000,
                                fx_pair=fxpair,
                                amount_remaining=100,
                                average_price=1.23,
                                commission=1.0,
                                cntr_commission=0.5,
                                company_hedge_action=action,
                                state=OMSOrderTicket.States.STAGED)
        self.assertEqual(ticket.amount_filled, 10000)
        self.assertEqual(ticket.fx_pair, fxpair)
        self.assertEqual(ticket.amount_remaining, 100)
        self.assertEqual(ticket.average_price, 1.23)
        self.assertEqual(ticket.commission, 1.0)
        self.assertEqual(ticket.cntr_commission, 0.5)
        self.assertEqual(ticket.company_hedge_action, action)
        self.assertEqual(ticket.state, OMSOrderTicket.States.STAGED)

        self.assertEqual(ticket.total_price, 12300)


if __name__ == '__main__':
    unittest.main()
