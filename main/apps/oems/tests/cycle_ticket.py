from datetime import datetime, timedelta

import pytest
# import unittest

from pytest_subtests.plugin import subtests
from zope.interface import named

from main.apps.account.models import Company
from main.apps.broker.models import BrokerInstrument, Broker, BrokerCompanyInstrument, BrokerUserInstrument, \
    FundingModel
from main.apps.currency.models import Currency, FxPair, CurrencyTypes
from main.apps.marketdata.models import Instrument, InstrumentTypes, TradingCalendarFincal, CorpayFxSpot, DataCut
from main.apps.oems.backend.oms import OmsBase
from main.apps.oems.backend.states import INTERNAL_STATES, PHASES
from main.apps.oems.models import Ticket, CnyExecution
from hdlib.DateTime.Date import Date

from django.db import connection

from main.apps.oems.tests.conftest import create_user


@pytest.fixture
def setup_data(create_currency, create_pair):
    def _run():

        currency_1 = create_currency("USD")
        currency_2 = create_currency("EUR")

        fx = create_pair(currency_1, currency_2)

        company = Company.create_company(name="Test company", currency="USD")

        from_ccy = currency_1
        to_ccy = currency_2

        market_name = fx.market

        all_in_rate = 83.4028
        all_in_cntr_done = 2_000_000  # all_in_done * all_in_rate
        all_in_done = round(all_in_cntr_done / all_in_rate, 2)
        spot_rate = 83.3775
        fwd_points = round(all_in_rate - spot_rate, 9)
        value_date = Date.from_int(20240430)
        fixing_date = Date.from_int(20240426)
        transaction_time = '2024-04-12T04:11:04.002417'


        ticket = Ticket.objects.create(
            company=company,
            sell_currency=from_ccy,
            buy_currency=to_ccy,
            market_name=market_name,
            side='sell',
            amount=all_in_cntr_done,
            lock_side=to_ccy,
            tenor='fwd',
            value_date=value_date,
            fixing_date=fixing_date,
            instrument_type='ndf',
            draft=False,
            time_in_force='1min',
            ticket_type='PAYMENT',
            # action=ticket_action,
            execution_strategy='market',
            trader='teste',
            all_in_done=all_in_done,
            all_in_rate=all_in_rate,
            transaction_time=transaction_time,
            all_in_cntr_done=all_in_cntr_done,
            spot_rate=spot_rate,
            fwd_points=fwd_points,
            # internal_state=initial_ticket_state
        )

        oms = OmsBase
        oms = oms(oms_id="TEST", oms_typ="test")

        return ticket, oms
    return _run

@pytest.mark.django_db
def test_oms_ticket_new(setup_data):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.NEW
    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.PENDAUTH

@pytest.mark.django_db
def test_oms_ticket_pend_auth_rfq(setup_data):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.PENDAUTH
    ticket.action = Ticket.Actions.RFQ
    ticket.destination =  "Test"
    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.ACCEPTED
    assert ticket.phase == PHASES.WORKING

@pytest.mark.django_db
def test_oms_ticket_pend_auth_premargined(setup_data):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.PENDAUTH
    ticket.funding =  FundingModel.PREMARGINED
    ticket.auth_user = "Test"
    ticket.destination = "Test"
    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.ACCEPTED
    assert ticket.phase == PHASES.WORKING

@pytest.mark.django_db
def test_oms_ticket_pendfund(setup_data):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.PENDFUNDS

    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.PENDFUNDS

@pytest.mark.django_db
def test_oms_ticket_scheduled(setup_data):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.SCHEDULED

    now = datetime.now()
    ticket.start_time = now
    ticket.destination = "Test"

    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.ACCEPTED

@pytest.mark.django_db
def test_oms_ticket_pendpause(setup_data):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.PENDPAUSE

    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.PENDPAUSE


@pytest.mark.django_db
def test_oms_ticket_pendresume(setup_data):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.PENDRESUME

    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.PENDRESUME

@pytest.mark.django_db
def test_oms_ticket_waiting_bestex(setup_data, create_user):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    company = Company.create_company(name="Test company", currency=Currency.get_currency("USD"))

    fx = FxPair.get_pair("USD/EUR")

    CnyExecution.objects.create(company=company, fxpair=fx)

    instrument = Instrument.objects.create(
        name = "USDEUR",
        instrument_type=InstrumentTypes.SPOT ,
        tradable_instrument=True,
        multi_leg=False,
        base_instrument="USDEUR",
        symbology=
        {
             "c4":{"TENOR":"SPOT","MARKET":"USDEUR","TENORS":{"1M":True,"1W":True,"1Y":True,"2D":False,"2M":True,"2W":True,"2Y":False,"3D":False,"3M":True,"3W":True,"4M":True,"5M":True,"6M":True,"7M":False,"8M":False,"9M":True,"ON":False,"SN":True,"SW":False,"TN":False,"EOM1":False,"EOM2":False,"EOM3":False,"EOM4":False,"EOM5":False,"EOM6":False,"IMM1":False,"IMM2":False,"IMM3":False,"IMM4":False,"SPOT":True},"QT_SPEC":4,"BASE_CCY":"USD","CCY_TYPE":"Spot","CNTR_CCY":"EUR","TIMEZONE":"America/New_York","VOL_TYPE":"log_rtn","TICK_TYPE":"mid","INSTR_TYPE":"FX","DESCRIPTION":"Euro","CALENDAR_CODE":"STANDARD","DELIVERY_TYPE":"Deliverable","SETTLEMENT_DAYS":2,"TERM_STRUCTURE_FIT":"linear"},
             "FINCAL": {"CEN_CODE": "ZARA", "ALT_CEN_CODE": None, "EXEC_CEN_CODE": "ZARE", "HOL_CAL_CODES": ["NYB"], "WEEKEND_CEN_CODE": None}
        },
        reference={"TENOR": "SPOT", "MARKET": "USDEUR", "QT_SPEC": 4, "BASE_CCY": "USD", "CCY_TYPE": "Spot", "CNTR_CCY": "EUR", "TIMEZONE": "Africa/Lagos", "VOL_TYPE": "log_rtn", "TICK_TYPE": "mid", "INSTR_TYPE": "FX", "DESCRIPTION": "Any", "CALENDAR_CODE": "STANDARD", "DELIVERY_TYPE": "Deliverable", "SETTLEMENT_DAYS": 2,
 }
    )
    _, broker = Broker.create_broker("Test")
    broker_instrument = BrokerInstrument.objects.create(
        broker = broker,
        instrument=instrument

    )
    BrokerCompanyInstrument.objects.create(
        company = company,
        broker_instrument=broker_instrument,
    )

    user = create_user()
    BrokerUserInstrument.objects.create(
        user = user,
        company = company,
        broker_instrument= broker_instrument,
    )
    # curr_date = Date.today()
    # curr_date = Date.from_int(20240405)
    curr_date = Date.from_str("2024-09-18")
    gmtt_open = (curr_date - timedelta(days=1))
    gmtt_close = (curr_date + timedelta(days=2))

    TradingCalendarFincal.objects.create(
        trade_date=curr_date.strftime("%Y-%m-%d"),
        activity='Synthetic Continuous Trading',
        gmtt_open=gmtt_open.strftime("%Y-%m-%dT%H:%M:%SZ"),
        gmtt_close=gmtt_close.strftime("%Y-%m-%dT%H:%M:%SZ"),
        cen_code='ZARE',
        functions='1 2 3 4L 4M 9F',
        market='Exec Deliverable Currencies'
    )
    CorpayFxSpot.objects.create(
        pair = fx,
        date=curr_date.strftime("%Y-%m-%d"),
        data_cut = DataCut.create_cut(time = curr_date, cut_type= DataCut.CutType.EOD)
    )

    ticket.internal_state = INTERNAL_STATES.WAITING
    ticket.upper_trigger = 0.1
    # BESTX
    ticket.execution_strategy = Ticket.ExecutionStrategies.BESTX
    ticket.destination = "Test"

    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.ACCEPTED


@pytest.mark.django_db
def test_oms_ticket_waiting_market(setup_data, create_user):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.WAITING
    ticket.upper_trigger = 0.1

    ticket.execution_strategy = Ticket.ExecutionStrategies.MARKET
    ticket.destination = "Test"

    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.ACCEPTED

@pytest.mark.django_db
def test_oms_ticket_waiting_market_strategix_execution(setup_data, create_user):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.WAITING

    ticket.execution_strategy = Ticket.ExecutionStrategies.STRATEGIC_EXECUTION

    ticket.destination = "Test"

    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.WAITING
    assert ticket.execution_status == "PENDING"

@pytest.mark.django_db
def test_oms_ticket_waiting_market_no_execution_strategy(setup_data, create_user):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.WAITING

    ticket.execution_strategy = None

    ticket.destination = "Test"

    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.ACCEPTED


@pytest.mark.django_db
def test_oms_ticket_accepted(setup_data, create_user):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.ACCEPTED
    ticket.destination = "Test"

    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.phase == PHASES.WORKING

@pytest.mark.django_db
def test_oms_ticket_pendcancel(setup_data, create_user):
    ticket, oms = setup_data()

    assert ticket is not None
    assert oms is not None

    ticket.internal_state = INTERNAL_STATES.PENDCANCEL

    ticket.save()

    oms.add_ticket(ticket)

    oms.cycle_tickets()

    ticket = Ticket.objects.get(id=ticket.id)
    assert ticket is not None

    assert ticket.internal_state == INTERNAL_STATES.PENDCANCEL