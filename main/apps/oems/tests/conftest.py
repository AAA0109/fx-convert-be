from datetime import date

import pytest
from rest_framework.authtoken.models import TokenProxy

from main.apps.account.models import User, Company
from main.apps.broker.models import Broker, ConfigurationTemplate
from main.apps.currency.models import Currency, FxPair
from main.apps.marketdata.models import TradingHolidaysFincal, Instrument


@pytest.fixture(scope="session")
def add_trading_holiday():
    def _run(code='NYB', holiday_date=date.today()):
        TradingHolidaysFincal.objects.create(
            date=holiday_date,
            code=code
        )

    return _run


@pytest.fixture(scope="session")
def create_currency():
    def _run(mnemonic='USD'):
        _, currency = Currency.create_currency(mnemonic, mnemonic, mnemonic)
        return currency

    return _run


@pytest.fixture(scope="session")
def create_pair(create_currency):
    def _run(currency1='USD', currency2='CAD'):
        cur1 = create_currency(currency1)  # type:Currency
        cur2 = create_currency(currency2)  # type:Currency
        FxPair.create_fxpair(cur2, cur1)
        _, pair = FxPair.create_fxpair(cur1, cur2)
        return pair

    return _run


@pytest.fixture(scope="session")
def create_auth_headers():
    def _run(user):
        token = TokenProxy.objects.create(user=user)
        return {
            'Authorization': f"Token {token.key}",
        }

    return _run


@pytest.fixture(scope="session")
def create_user(create_currency):
    def _run(email='test@test.com', password='123', company=None):
        if not company:
            usd = create_currency('USD')
            company = Company.objects.create(name='Test Company 1', currency=usd, status=Company.CompanyStatus.ACTIVE)

        user = User.objects.create_user(email=email, password=password, is_staff=True, is_superuser=True)
        user.company = company
        user.save()
        return user

    return _run

@pytest.fixture(scope="session")
def create_spot_instrument():
    def _run(market="USDEUR"):
        reference_data = {"TENOR": "SPOT", "MARKET": market,
         "TENORS": {"1M": True, "1W": True, "1Y": True, "2D": False, "2M": True, "2W": True, "2Y": False, "3D": False,
                    "3M": True, "3W": True, "4M": True, "5M": True, "6M": True, "7M": False, "8M": False, "9M": True,
                    "ON": False, "SN": True, "SW": False, "TN": False, "EOM1": False, "EOM2": False, "EOM3": False,
                    "EOM4": False, "EOM5": False, "EOM6": False, "IMM1": False, "IMM2": False, "IMM3": False, "IMM4": False,
                    "SPOT": True},
          "QT_SPEC": 4, "BASE_CCY": "USD", "CCY_TYPE": "Spot", "CNTR_CCY": "EUR",
         "TIMEZONE": "America/New_York", "VOL_TYPE": "log_rtn", "TICK_TYPE": "mid", "INSTR_TYPE": "FX",
         "DESCRIPTION": "Euro", "CALENDAR_CODE": "STANDARD", "DELIVERY_TYPE": "Deliverable", "SETTLEMENT_DAYS": 2,
         "TERM_STRUCTURE_FIT": "linear"}
        symbology_data = {"BBG": {"FIGI": "BBG0013HQHV6"}, "IBKR": {},
             "FINCAL": {"CEN_CODE": "DCCY", "ALT_CEN_CODE": None, "EXEC_CEN_CODE": "DCCE", "HOL_CAL_CODES": ["NYB", "Tgt"],
                        "WEEKEND_CEN_CODE": None}, "REUTERS": {}}


        instrument = Instrument.objects.create(
            name=market,
            instrument_type="spot",
            tradable_instrument=True,
            base_instrument=market,
            reference= reference_data,
            symbology= symbology_data,
        )
        return instrument
    return _run

@pytest.fixture(scope="session")
def create_broker():
    def _run(name="Corpay", provider="CORPAY", instruments=["spot"]):
        broker = Broker.objects.create(name=name,
                                       broker_provider=provider,
                                       supported_instruments=instruments
                                       )
        return broker

    return _run

@pytest.fixture(scope="session")
def create_configuration_template():
    def _run(sell_currency_id, buy_currency_id, preferred_broker_id, instrument_type = 'spot', broker_markup = 10):
        cfg = ConfigurationTemplate.objects.create(sell_currency_id=sell_currency_id,
                                                   buy_currency_id=buy_currency_id,
                                                   broker_markup=broker_markup,
                                                   preferred_broker_id=preferred_broker_id,
                                                   instrument_type=instrument_type
                                                   )
        return cfg

    return _run

