from datetime import datetime, timedelta
from django.test import TestCase
from main.apps.account.models.company import Company

from main.apps.broker.models.broker import Broker
from main.apps.broker.models.constants import BrokerProviderOption
from main.apps.broker.models.fee import BrokerFeeCompany
from main.apps.broker.services.fee import BrokerFeeProvider
from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.models.ref.instrument import InstrumentTypes
from main.apps.oems.models.cny import CnyExecution
from main.apps.oems.models.ticket import Ticket


class TestFeeProvider(TestCase):

    def setUp(self) -> None:
        super().setUp()
        instruments = [InstrumentTypes.SPOT, InstrumentTypes.FORWARD]

        self.fees = {
            'usd_eur_spot': {
                'pangea_fee': 0.005,
                'broker_fee': 0.005
            },
            'usd_eur_forward': {
                'pangea_fee': 0.006,
                'broker_fee': 0.006
            },
            'eur_usd_spot': {
                'pangea_fee': 0.005,
                'broker_fee': 0.005
            },
            'eur_usd_forward': {
                'pangea_fee': 0.006,
                'broker_fee': 0.006
            },
            'usd_mxn_spot': {
                'pangea_fee': 0.008,
                'broker_fee': 0.008
            },
            'usd_mxn_forward': {
                'pangea_fee': 0.01,
                'broker_fee': 0.01
            },
            'mxn_usd_spot': {
                'pangea_fee': 0.008,
                'broker_fee': 0.008
            },
            'mxn_usd_forward': {
                'pangea_fee': 0.01,
                'broker_fee': 0.01
            },
            'eur_mxn_spot': {
                'pangea_fee': 0.004,
                'broker_fee': 0.004
            },
            'eur_mxn_forward': {
                'pangea_fee': 0.007,
                'broker_fee': 0.007
            },

        }

        # Create Monex broker
        self.broker_monex = Broker.objects.create(
            name="Monex",
            broker_provider=BrokerProviderOption.MONEX
        )

        # Create currencies
        self.currencies = {
            'usd': Currency.objects.create(mnemonic='USD', name="US Dollar"),
            'eur': Currency.objects.create(mnemonic='EUR', name="Euro"),
            'mxn': Currency.objects.create(mnemonic='MXN', name="Mexican Peso"),
        }

        # Create a company
        self.company = Company.objects.create(name="Test Company",
                                              currency=self.currencies['usd'])

        # Create fx pairs
        # Fx pairs dict will have key pattern like ccy1_ccy2
        # e.g. usd_eur or eur_usd
        self.pairs = {}
        for key, value in self.currencies.items():
            for key2, value2 in self.currencies.items():
                self.pairs[f'{key}_{key2}'] = FxPair.objects.create(base_currency=value,
                                                                    quote_currency=value2)

        # Create company fees
        # Company fees dict will have key pattern like ccy1_ccy2_instrument
        # e.g. usd_eur_spot or usd_eur_forward
        company_fees = {}
        fee_keys = self.fees.keys()
        for key, value in self.pairs.items():
            splits = key.split('_')
            if splits[0] != splits[1]:
                for instrument in instruments:
                    fee_key = '_'.join([splits[0], splits[1], instrument])
                    if fee_key in fee_keys:
                        company_fees[fee_key] = BrokerFeeCompany.objects.create(
                                                    company=self.company,
                                                    broker=self.broker_monex,
                                                    sell_currency=value.base_currency,
                                                    buy_currency=value.quote_currency,
                                                    instrument_type=instrument,
                                                    broker_fee=self.fees[fee_key]['broker_fee'],
                                                    pangea_fee=self.fees[fee_key]['pangea_fee']
                                                )

        # Create cny executions
        for key, value in self.pairs.items():
            splits = key.split('_')
            if splits[0] != splits[1]:
                CnyExecution.objects.create(
                    company=self.company,
                    fxpair=self.pairs[key],
                    spot_broker=self.broker_monex.broker_provider,
                    fwd_broker=self.broker_monex.broker_provider,
                    spot_rfq_type=CnyExecution.RfqTypes.API,
                )

        self.ticket_eur_mxn_spot = Ticket.objects.create(
            company=self.company,
            broker=self.broker_monex.broker_provider,
            sell_currency=self.currencies['eur'],
            buy_currency=self.currencies['mxn'],
            market_name=self.pairs['eur_mxn'].market,
            side='sell',
            amount=100,
            lock_side=self.currencies['eur'],
            tenor='spot',
            value_date=datetime.now().date(),
            fixing_date=(datetime.now() + timedelta(days=3)).date(),
            instrument_type='spot',
            draft=True,
            time_in_force='1min',
            ticket_type='PAYMENT',
            execution_strategy='market',
            trader='test',
            spot_rate=21.78
        )

        fwd_ticket_date = datetime.now() + timedelta(days=15)
        self.ticket_eur_mxn_forward = Ticket.objects.create(
            company=self.company,
            broker=self.broker_monex.broker_provider,
            sell_currency=self.currencies['eur'],
            buy_currency=self.currencies['mxn'],
            market_name=self.pairs['eur_mxn'].market,
            side='sell',
            amount=100,
            lock_side=self.currencies['eur'],
            tenor='fwd',
            value_date=fwd_ticket_date.date(),
            fixing_date=(fwd_ticket_date + timedelta(days=5)).date(),
            instrument_type='fwd',
            draft=True,
            time_in_force='1min',
            ticket_type='PAYMENT',
            execution_strategy='market',
            trader='test',
            spot_rate=22.90
        )

    def tearDown(self) -> None:
        super().tearDown()

    def test_broker_fee_spot_sell_buy(self):
        now = datetime.now()
        usd_eur_rate = 0.90

        # Test spot sell
        fee_svc = BrokerFeeProvider(company=self.company)
        broker_fee, broker_fee_pct = fee_svc.get_indicative_broker_fee(
            rate=usd_eur_rate, fxpair=self.pairs['usd_eur'], tenor='spot', spot_dt=now.date(), side='Sell'
        )
        # Check if broker fee and broker fee pct is negative
        self.assertTrue('-' in str(broker_fee))
        self.assertTrue('-' in str(broker_fee_pct))

        self.assertEqual(abs(broker_fee), round(self.fees['usd_eur_spot']['broker_fee'] * usd_eur_rate, 4))
        self.assertEqual(abs(broker_fee_pct), round(self.fees['usd_eur_spot']['broker_fee'] * 100, 2))

        # Test spot buy
        fee_svc = BrokerFeeProvider(company=self.company)
        broker_fee, broker_fee_pct = fee_svc.get_indicative_broker_fee(
            rate=usd_eur_rate, fxpair=self.pairs['usd_eur'], tenor='spot', spot_dt=now.date(), side='Buy'
        )
        # Check if broker fee and broker fee pct is not negative
        self.assertTrue('-' not in str(broker_fee))
        self.assertTrue('-' not in str(broker_fee_pct))

        self.assertEqual(abs(broker_fee), round(self.fees['usd_eur_spot']['broker_fee'] * usd_eur_rate, 4))
        self.assertEqual(abs(broker_fee_pct), round(self.fees['usd_eur_spot']['broker_fee'] * 100, 2))

    def test_broker_fee_fwd_sell_buy(self):
        now = datetime.now()
        fwd_date = now + timedelta(days=5)
        mxn_usd_rate = 0.051

        # Test fwd sell
        fee_svc = BrokerFeeProvider(company=self.company)
        broker_fee, broker_fee_pct = fee_svc.get_indicative_broker_fee(
            rate=mxn_usd_rate, fxpair=self.pairs['mxn_usd'], tenor=fwd_date.date(), spot_dt=now.date(), side='Sell'
        )
        # Check if broker fee and broker fee pct is negative
        self.assertTrue('-' in str(broker_fee))
        self.assertTrue('-' in str(broker_fee_pct))

        self.assertEqual(abs(broker_fee), round(self.fees['mxn_usd_forward']['broker_fee'] * mxn_usd_rate, 4))
        self.assertEqual(abs(broker_fee_pct), round(self.fees['mxn_usd_forward']['broker_fee'] * 100, 2))

        # Test fwd buy
        fee_svc = BrokerFeeProvider(company=self.company)
        broker_fee, broker_fee_pct = fee_svc.get_indicative_broker_fee(
            rate=mxn_usd_rate, fxpair=self.pairs['mxn_usd'], tenor=fwd_date.date(), spot_dt=now.date(), side='Buy'
        )
        # Check if broker fee and broker fee pct is not negative
        self.assertTrue('-' not in str(broker_fee))
        self.assertTrue('-' not in str(broker_fee_pct))

        self.assertEqual(abs(broker_fee), round(self.fees['mxn_usd_forward']['broker_fee'] * mxn_usd_rate, 4))
        self.assertEqual(abs(broker_fee_pct), round(self.fees['mxn_usd_forward']['broker_fee'] * 100, 2))

    def test_ticket_broker_fee_spot(self):
        fee_svc = BrokerFeeProvider(company=self.company)
        broker_fee, broker_fee_pct = fee_svc.get_broker_fee_from_ticket(ticket=self.ticket_eur_mxn_spot)

        self.assertEqual(broker_fee,
                         round(self.fees['eur_mxn_spot']['broker_fee'] * self.ticket_eur_mxn_spot.spot_rate, 4))
        self.assertEqual(abs(broker_fee_pct), round(self.fees['eur_mxn_spot']['broker_fee'] * 100, 2))

    def test_ticket_broker_fee_spot(self):
        fee_svc = BrokerFeeProvider(company=self.company)
        broker_fee, broker_fee_pct = fee_svc.get_broker_fee_from_ticket(ticket=self.ticket_eur_mxn_spot)

        self.assertEqual(broker_fee,
                         round(self.fees['eur_mxn_spot']['broker_fee'] * self.ticket_eur_mxn_spot.spot_rate, 4))
        self.assertEqual(abs(broker_fee_pct), round(self.fees['eur_mxn_spot']['broker_fee'] * 100, 2))

    def test_ticket_broker_fee_fwd(self):
        fee_svc = BrokerFeeProvider(company=self.company)
        broker_fee, broker_fee_pct = fee_svc.get_broker_fee_from_ticket(ticket=self.ticket_eur_mxn_forward)

        self.assertEqual(broker_fee,
                         round(self.fees['eur_mxn_forward']['broker_fee'] * self.ticket_eur_mxn_forward.spot_rate, 4))
        self.assertEqual(abs(broker_fee_pct), round(self.fees['eur_mxn_forward']['broker_fee'] * 100, 2))
