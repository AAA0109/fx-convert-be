import logging
from datetime import datetime, time, timedelta, timezone
from typing import Union, List

import pytz
from django.conf import settings
from hdlib.Core import Currency as HdlibCurrency
from rest_framework import serializers

from main.apps.account.models import Company
from main.apps.account.models.user import User
from main.apps.broker.models import BrokerCompanyInstrument, BrokerInstrument, Broker, \
    BrokerCompany, BrokerProviderOption
from main.apps.corpay.models import Beneficiary as CorpayBeneficiary, SettlementAccount, FXBalanceAccount
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.models import InstrumentTypes
from main.apps.nium.services.api.connectors.client.client_prefund_account import NiumPrefundAccountConnector
from main.apps.nium.services.api.connectors.testing.payin import NiumTestingPayInConnector
from main.apps.nium.services.api.dataclasses.client import ClientPrefundPayload
from main.apps.nium.services.api.dataclasses.testing import SimulateRcvTrxPayload
from main.apps.oems.backend.api import pangea_client
from main.apps.oems.backend.calendar_utils import infer_valid_settlement_day, get_fx_settlement_info, get_fx_fixing_dt, \
    get_spot_dt, get_trade_date_from_value_date, TENOR_MAP
from main.apps.oems.backend.ccy_utils import determine_rate_side
from main.apps.oems.backend.exec_utils import get_best_execution_status
from main.apps.oems.backend.trading_utils import get_reference_data
from main.apps.oems.models.cny import CnyExecution
from main.apps.oems.models.ticket import Ticket
from main.apps.settlement.models import BeneficiaryBroker, Beneficiary, Wallet

# TODO: put field-level validation here

# TODO: we need model level validation as validation depends on other field values

logger = logging.getLogger(__name__)


# ==============

class Brokers:
    CORPAY = 'CORPAY'
    CORPAY_MP = 'CORPAY_MP'
    VERTO = 'VERTO'
    NIUM = 'NIUM'
    AZA = 'AZA'
    MONEX = 'MONEX'
    CONVERA = 'CONVERA'
    OFX = 'OFX'
    XE = 'XE'
    IBKR = 'IBKR'
    OANDA = 'OANDA'
    AIRWALLEX = 'AIRWALLEX'


# =============

def get_funding_style(broker, instrument_type):
    funding = Ticket.FundingModel.PREFUNDED

    if broker == Brokers.CORPAY:
        return Ticket.FundingModel.POSTFUNDED
    elif broker == Brokers.CORPAY_MP:
        return Ticket.FundingModel.POSTFUNDED
    elif broker == Brokers.NIUM:
        return Ticket.FundingModel.PREFUNDED
    elif broker == Brokers.IBKR:
        return Ticket.FundingModel.PREMARGINED
    else:
        return funding


def check_max_tenor(value_date, exec_cfg, perm_cfg):
    days = (value_date - type(value_date).today()).days
    if perm_cfg and (days > perm_cfg.max_tenor_months * 31):
        raise serializers.ValidationError("Value date exceed max tenor")
    if exec_cfg['max_tenor'] in TENOR_MAP and days > TENOR_MAP[exec_cfg['max_tenor']]:
        raise serializers.ValidationError("Value date exceed max tenor")


def route_ticket(attrs, exec_cfg, validate=True, check_company=True ):
    if isinstance(attrs, dict):
        dest = attrs.get('destination', None)
        action = attrs['action']
        instrument_type = attrs['instrument_type']
        tenor = attrs['tenor']
        broker = attrs.get('broker', None)
        action = attrs.get('action')
        value_date = attrs.get('value_date')
    else:
        dest = attrs.destination
        action = attrs.action
        instrument_type = attrs.instrument_type
        tenor = attrs.tenor
        broker = attrs.broker
        action = attrs.action
        value_date = attrs.value_date

    # print( dest, action, instrument_type, tenor, broker )

    if broker == Brokers.CORPAY:
        if action == Ticket.Actions.RFQ:
            if instrument_type == Ticket.InstrumentTypes.SPOT:
                dest = 'RFQ'  # or RFQ_MP
            elif instrument_type in (Ticket.InstrumentTypes.FWD, Ticket.InstrumentTypes.NDF):
                dest = 'RFQ'
            else:
                raise serializers.ValidationError("Unsupported instrument.")
        elif action == Ticket.Actions.EXECUTE:
            if instrument_type == Ticket.InstrumentTypes.SPOT:
                dest = 'CORPAY'  # or RFQ_MP
            elif instrument_type in (Ticket.InstrumentTypes.FWD, Ticket.InstrumentTypes.NDF):
                dest = 'CORPAY'
            else:
                raise serializers.ValidationError("Unsupported instrument.")
    elif broker == Brokers.CORPAY_MP:
        if action == Ticket.Actions.RFQ:
            if instrument_type == Ticket.InstrumentTypes.SPOT:
                dest = 'RFQ'  # or RFQ_MP
            else:
                raise serializers.ValidationError("Unsupported instrument.")
        elif action == Ticket.Actions.EXECUTE:
            if instrument_type == Ticket.InstrumentTypes.SPOT:
                dest = 'CORPAY'  # or RFQ_MP
            else:
                raise serializers.ValidationError("Unsupported instrument.")
    elif broker == Brokers.MONEX:
        if action == Ticket.Actions.RFQ:
            if instrument_type == Ticket.InstrumentTypes.SPOT:
                dest = 'RFQ'  # or RFQ_MP
            elif instrument_type in (Ticket.InstrumentTypes.FWD, Ticket.InstrumentTypes.NDF):
                dest = 'RFQ'
            else:
                raise serializers.ValidationError("Unsupported instrument.")
        elif action == Ticket.Actions.EXECUTE:
            if instrument_type == Ticket.InstrumentTypes.SPOT:
                dest = 'CORPAY'  # or RFQ_MP
            elif instrument_type in (Ticket.InstrumentTypes.FWD, Ticket.InstrumentTypes.NDF):
                dest = 'CORPAY'
            else:
                raise serializers.ValidationError("Unsupported instrument.")
    elif broker == Brokers.NIUM:
        if action == Ticket.Actions.RFQ:
            if instrument_type == Ticket.InstrumentTypes.SPOT:
                dest = 'RFQ'  # or RFQ_MP
            else:
                raise serializers.ValidationError("Unsupported instrument.")
        elif action == Ticket.Actions.EXECUTE:
            if instrument_type == Ticket.InstrumentTypes.SPOT:
                dest = 'CORPAY'  # or RFQ_MP
            else:
                raise serializers.ValidationError("Unsupported instrument.")
    elif not broker:
        if action == Ticket.Actions.RFQ:
            brk_fld = f'{tenor}_broker'
            dest_fld = f'{tenor}_rfq_dest'
        elif action == Ticket.Actions.EXECUTE:
            brk_fld = f'{tenor}_broker'
            dest_fld = f'{tenor}_dest'
            # minimum quote time for executions
            attrs['time_in_force'] = Ticket.TimeInForces._10SEC
        else:
            raise serializers.ValidationError("Unsupported action.")
        attrs['broker'] = exec_cfg[brk_fld]
        dest = exec_cfg[dest_fld]
    else:
        raise serializers.ValidationError("Routing not configured.")

    if not dest:
        raise serializers.ValidationError("Routing not configured.")

    if isinstance(attrs, dict):
        attrs['destination'] = dest
        attrs['funding'] = get_funding_style(attrs['broker'], instrument_type)
    else:
        attrs.destination = dest
        attrs.funding = get_funding_style(attrs.broker, instrument_type)

    if validate:
        perm_cfg = validate_instrument_amount(attrs, check_company=check_company)
    else:
        perm_cfg = None

    # rfq type stuff
    # TODO: could get the rfq type from the BrokerInstrument

    check_max_tenor(value_date, exec_cfg, perm_cfg)

    if isinstance(attrs, dict):
        if attrs.get('with_care'):
            attrs['rfq_type'] = CnyExecution.RfqTypes.MANUAL
        else:
            attrs['rfq_type'] = exec_cfg[f'{tenor}_rfq_type']

        if attrs['rfq_type'] == CnyExecution.RfqTypes.UNSUPPORTED:
            raise serializers.ValidationError("This market is not supported.")

        if action == Ticket.Actions.EXECUTE and action == CnyExecution.RfqTypes.MANUAL:
            attrs['rfq_type'] = CnyExecution.RfqTypes.NORFQ
        elif action == Ticket.Actions.RFQ and action == CnyExecution.RfqTypes.MANUAL:
            # only if fwd
            attrs['rfq_type'] = CnyExecution.RfqTypes.INDICATIVE

        if not attrs.get('execution_strategy'):
            attrs['execution_strategy'] = exec_cfg['default_exec_strat']
    else:
        if attrs.with_care:
            attrs.rfq_type = CnyExecution.RfqTypes.MANUAL
        else:
            attrs.rfq_type = exec_cfg[f'{tenor}_rfq_type']

        if attrs.rfq_type == CnyExecution.RfqTypes.UNSUPPORTED:
            raise serializers.ValidationError("This market is not supported.")

        if action == Ticket.Actions.EXECUTE and attrs.rfq_type == CnyExecution.RfqTypes.MANUAL:
            attrs.rfq_type = CnyExecution.RfqTypes.NORFQ
        elif action == Ticket.Actions.RFQ and attrs.rfq_type == CnyExecution.RfqTypes.MANUAL:
            # only if fwd
            attrs.rfq_type = CnyExecution.RfqTypes.INDICATIVE

        if not attrs.execution_strategy:
            attrs.execution_strategy = exec_cfg['default_exec_strat']

    return dest


# ===========

def validate_corpay_beneficiary(ccy: HdlibCurrency,
                                beneficiary: Union[Beneficiary, CorpayBeneficiary, FXBalanceAccount]):
    if ccy.get_mnemonic() != beneficiary.destination_currency.mnemonic:
        raise serializers.ValidationError(
            "Destination currency does not match origin currency.")


def validate_corpay_beneficiaries(ccy: HdlibCurrency, beneficiaries: List, company: Company):
    beneficiary_ids = [b['beneficiary_id'] for b in beneficiaries]
    broker = Broker.objects.get(
        broker_provider=BrokerProviderOption.CORPAY)
    # Fetch all relevant wallets and beneficiaries in bulk
    wallets = {str(w.wallet_id): w for w in Wallet.objects.filter(
        wallet_id__in=beneficiary_ids, broker=broker)}
    beneficiary_brokers = {
        str(bb.beneficiary.beneficiary_id): bb
        for bb in BeneficiaryBroker.objects.filter(beneficiary__beneficiary_id__in=beneficiary_ids,
                                                   broker=broker)
        .select_related('beneficiary', 'broker')
    }

    for beneficiary in beneficiaries:
        beneficiary_id = beneficiary['beneficiary_id']
    wallet = wallets.get(beneficiary_id)
    beneficiary_broker = beneficiary_brokers.get(beneficiary_id)

    if not wallet and not beneficiary_broker:
        raise serializers.ValidationError(
            "Destination account does not exist, "
            "please contact our support team to resolve this issue"
        )

    destination = wallet or beneficiary_broker.beneficiary
    broker = wallet.broker if wallet else beneficiary_broker.broker

    if broker.broker_provider != BrokerProviderOption.CORPAY:
        raise serializers.ValidationError(
            "Destination broker does not match ticket broker, "
            "please contact our support team to resolve this issue"
        )

    destination_currency = wallet.currency if wallet else destination.destination_currency
    if destination_currency.mnemonic != ccy.mnemonic:
        raise serializers.ValidationError(
            "Destination currency does not match ticket currency, "
            "please contact our support team to resolve this issue"
        )


def validate_corpay_settlement_account(ccy: HdlibCurrency, settlement_info: [SettlementAccount, Wallet]):
    if ccy.get_mnemonic() != settlement_info.currency.mnemonic:
        raise serializers.ValidationError(
            "Settlement account does not match currency, "
            "please contact our support team to resolve this issue"
        )


def validate_corpay_settlement_info(ccy: HdlibCurrency, settlement_info_list: List, company: Company):
    for settlement_info in settlement_info_list:
        wallet = Wallet.objects.get(
            wallet_id=settlement_info['settlement_account_id'])
        if not wallet:
            raise serializers.ValidationError(
                "Origin account does not exist, "
                "please contact our support team to resolve this issue"
            )
        if ccy.get_mnemonic() != wallet.currency.mnemonic:
            raise serializers.ValidationError(
                "Origin currency does not match ticket currency, "
                "please contact our support team to resolve this issue"
            )


def validate_corpay_different(beneficiaries, settlement_info):
    tracker = set()
    for bene in beneficiaries:
        key = bene['beneficiary_id']
        if not key:
            raise serializers.ValidationError('No beneficiary id')
        if key in tracker:
            raise serializers.ValidationError(
                "Must use different origin and destination accounts")
        else:
            tracker.add(key)
    for bene in settlement_info:
        key = bene['settlement_account_id']
        if not key:
            raise serializers.ValidationError('No settlement account id')
        if key in tracker:
            raise serializers.ValidationError(
                "Must use different origin and destination accounts")
        else:
            tracker.add(key)


def shared_ticket_bene_validation(attrs):
    # check that settlement_info and beneciary are valid for currencies
    # raise serializers.ValidationError() if problem!

    # TODO: set default wallets so we can at least complete the trade?

    if isinstance(attrs, dict):
        funding = attrs['funding']
        broker = attrs['broker']
        action = attrs['action']
        sell_currency = attrs['sell_currency']
        buy_currency = attrs['buy_currency']
        company = attrs['company']
    else:
        funding = attrs.funding
        broker = attrs.broker
        action = attrs.action
        sell_currency = attrs.sell_currency
        buy_currency = attrs.buy_currency
        company = attrs.company
        attrs = vars(attrs)  # hack and wont handle foreign keys

    if funding == Ticket.FundingModel.PREFUNDED:
        # check that settlement_info + beneficiary_id is provided and valid
        # for the currency transaction
        # could set default wallets here if we wanted...
        # Nium works like this...
        if broker == Brokers.NIUM:
            if attrs.get('beneficiaries'):
                validate_corpay_beneficiaries(
                    buy_currency, attrs['beneficiaries'], company)
            if attrs.get('settlement_info'):
                validate_corpay_settlement_info(
                    sell_currency, attrs['settlement_info'], company)
            try:
                if settings.APP_ENVIRONMENT in ['local', 'development']:
                    nium_test_api = NiumTestingPayInConnector()
                    payload = SimulateRcvTrxPayload(
                        amount=0,
                        bankReferenceNumber='',
                        bankSource='',
                        country='',
                        currency=''
                    )
                    response = nium_test_api.simulate_receiving_transaction(
                        data=payload)
                else:
                    nium_client_api = NiumPrefundAccountConnector()
                    payload = ClientPrefundPayload(
                        amount=0,
                        currencyCode=''
                    )
                    response = nium_client_api.client_prefund_request(
                        data=payload)
            except Exception as e:
                pass
    elif funding == Ticket.FundingModel.POSTFUNDED:

        if broker == Brokers.CORPAY or broker == Brokers.CORPAY_MP:
            if action == Ticket.Actions.RFQ:
                if attrs.get('beneficiaries'):
                    validate_corpay_beneficiaries(
                        buy_currency, attrs['beneficiaries'], company)
                if attrs.get('settlement_info'):
                    validate_corpay_settlement_info(
                        sell_currency, attrs['settlement_info'], company)
                # CORPAY MP needs beneficiaries
                if broker == Brokers.CORPAY:
                    return
            if not 'beneficiaries' in attrs:
                raise serializers.ValidationError("Missing beneficiaries.")
            if not isinstance(attrs['beneficiaries'], list):
                raise serializers.ValidationError(
                    "beneficiaries should be a list")
            validate_corpay_beneficiaries(
                buy_currency, attrs['beneficiaries'], company)

            if not 'settlement_info' in attrs:
                raise serializers.ValidationError("Missing settlement info")
            if not isinstance(attrs['settlement_info'], list):
                raise serializers.ValidationError(
                    "settlement_info should be a list")
            validate_corpay_settlement_info(
                sell_currency, attrs['settlement_info'], company)
            validate_corpay_different(
                attrs['beneficiaries'], attrs['settlement_info'])
        ...
    elif funding == Ticket.FundingModel.PREMARGINED:
        # check that margin exists in the broker account
        # IBKR works like this
        ...
    elif funding == Ticket.FundingModel.POSTMARGINED:
        # TODO: make sure this is good to go on limit
        # corpay sometimes works like this for forwards
        ...


def evaluate_scheduled_spot(attrs):
    # this is a bit crazy given the way local currencies work for spot.
    trade_date = get_trade_date_from_value_date(
        attrs['market_name'], attrs['value_date'])

    # TODO: add a better time to execute using fixes
    start_time = datetime.combine(trade_date, time(15))
    attrs['start_time'] = start_time

    end = attrs.get('end_time')
    if end and end < start_time:
        raise serializers.ValidationError(
            "end_time issue with scheduled transaction")


def evaluate_smart_ex(attrs):
    # NOTE: this is a fake function to do SMART execution...
    from main.apps.oems.backend.utils import random_decision
    if random_decision(0.01):
        attrs['execution_strategy'] = Ticket.ExecutionStrategies.MARKET


def evaluate_best_ex(attrs, upper_bps=0.01, lower_bps=0.01):
    if isinstance(attrs, dict):

        attrs['execution_strategy'] = Ticket.ExecutionStrategies.TRIGGER

        # TODO: add spot triggers
        spot = None
        if spot is not None:
            if not attrs['upper_trigger']:
                attrs['upper_trigger'] = spot * (1.0 + upper_bps)
            if not attrs['lower_trigger']:
                attrs['lower_trigger'] = spot * (1.0 - lower_bps)

        if not attrs.get('trigger_time'):

            bestex = get_best_execution_status(attrs['market_name'],
                                               check_spot=(attrs['instrument_type'] == Ticket.InstrumentTypes.SPOT))

            if bestex['recommend']:
                attrs['execution_strategy'] = Ticket.ExecutionStrategies.MARKET
            else:

                if bestex['unsupported']:
                    raise serializers.ValidationError(
                        "This market does not support BESTX.")

                trigger_time = bestex['check_back']  # session['GMTT_OPEN']

                start = attrs.get('start_time')

                if start and start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)

                if start and start > trigger_time:
                    # TODO: need to evaluate BESTX now in OMS
                    # TODO: need to check if trigger tiem is compliant with schedule
                    # if this is a schedule spot transaction... pick the liquid benchmark time
                    # as start_time so that it does not execute at midnight UTC
                    attrs['execution_strategy'] = Ticket.ExecutionStrategies.BESTX
                else:
                    attrs['trigger_time'] = trigger_time

    else:

        # TODO: make this DRY
        attrs.execution_strategy = Ticket.ExecutionStrategies.TRIGGER

        # TODO: add spot triggers
        spot = None
        if spot is not None:
            # TODO: this should be 1 daily vol
            if not attrs.upper_trigger:
                attrs.upper_trigger = spot * (1.0 + upper_bps)
            if not attrs.lower_trigger:
                attrs.lower_trigger = spot * (1.0 - lower_bps)

        if not attrs.trigger_time:

            bestex = get_best_execution_status(attrs.market_name,
                                               check_spot=(attrs.instrument_type == Ticket.InstrumentTypes.SPOT))

            if bestex['recommend']:
                attrs.execution_strategy = Ticket.ExecutionStrategies.MARKET
            else:

                if bestex['unsupported']:
                    raise serializers.ValidationError(
                        "This market does not support BESTX.")

                trigger_time = bestex['check_back']  # session['GMTT_OPEN']

                start = attrs.start_time

                if start and start > trigger_time:
                    # TODO: need to evaluate BESTX now in OMS
                    # TODO: need to check if trigger tiem is compliant with schedule
                    # if this is a schedule spot transaction... pick the liquid benchmark time
                    # as start_time so that it does not execute at midnight UTC
                    attrs.execution_strategy = Ticket.ExecutionStrategies.BESTX
                else:
                    attrs.trigger_time = trigger_time


# ===========

def validate_amount(amount, lock_side):
    # check that amount is specified to at most the units of precision
    if amount is not None and isinstance(lock_side.unit, int):
        decimals = len(str(amount).split('.')[-1].rstrip('0'))
        if decimals > lock_side.unit:
            raise serializers.ValidationError(
                f"Amount specified to greater precision that lock_side currency allows: {decimals}")


def validate_instrument_amount(attrs, check_company=True):
    if isinstance(attrs, dict):
        lock_side = attrs.get('lock_side')
        sell_currency = attrs.get('sell_currency')
        buy_currency = attrs.get('buy_currency')
        broker_key = attrs.get('broker')
        company = attrs.get('company')
        market_name = attrs.get('market_name')
        tenor = attrs.get('tenor')
        instr_type = attrs.get('instrument_type')
        amount = attrs.get('amount')
        side = attrs.get('side')
    else:
        lock_side = attrs.get_lock_side()
        sell_currency = attrs.get_sell_currency()
        buy_currency = attrs.get_buy_currency()
        broker_key = attrs.broker
        company = attrs.get_company()
        market_name = attrs.market_name
        tenor = attrs.tenor
        instr_type = attrs.instrument_type
        amount = attrs.amount
        side = attrs.side

    # ====================

    validate_amount(amount, lock_side)

    ls = lock_side.get_mnemonic()

    if ls == sell_currency.get_mnemonic():
        _ls = 'buy' if side == 'Buy' else 'sell'
    elif ls == buy_currency.get_mnemonic():
        _ls = 'sell' if side == 'Buy' else 'buy'
    else:
        raise serializers.ValidationError(
            "Lock_side must be the buy or sell currency.")

    min_amount_fld = f'min_order_size_{_ls}'
    max_amount_fld = f'max_order_size_{_ls}'
    unit_amount_fld = f'unit_order_size_{_ls}'

    try:
        broker = Broker.objects.get(broker_provider=broker_key)
    except:
        raise serializers.ValidationError(f"Broker not found: {broker_key}")

    # ensure broker is turned on for company
    try:
        broker_company = BrokerCompany.objects.get(
            broker=broker_key, company=company)
    except:
        raise serializers.ValidationError(
            f"Broker not configured for company: {broker_key} {company.name}")

    if instr_type == InstrumentTypes.NDF:
        instrument_name = f'{market_name}-{tenor.upper()}'
    else:
        instrument_name = f"{market_name}-{instr_type.upper()}"

    try:
        if instr_type == InstrumentTypes.NDF:
            broker_instrument = BrokerInstrument.objects.get(broker=broker, instrument__name=instrument_name,
                                                             instrument__instrument_type=InstrumentTypes.NDF)
        else:
            broker_instrument = BrokerInstrument.objects.get(
                broker=broker, instrument__name=instrument_name)
    except:
        raise serializers.ValidationError(
            f"Broker is not configured for this instrument: {broker_key} {instrument_name}")

    if (side == 'Sell' and not broker_instrument.sell) or (side == 'Buy' and not broker_instrument.buy):
        raise serializers.ValidationError(
            f"Cannot trade this instrument side: {broker_key} {instrument_name} {side}")

    ret = None

    if check_company:

        try:
            company_permission = BrokerCompanyInstrument.objects.get(company=company,
                                                                     broker_instrument=broker_instrument)
        except:
            raise serializers.ValidationError(
                f"Company permission not found for this instrument: {company.name} {broker_key} {instrument_name}")

        ret = company_permission

        if not company_permission.active:
            raise serializers.ValidationError(
                f"Company instrument disabled: {company.name} {broker_key} {instrument_name}")

        if amount < getattr(company_permission, min_amount_fld):
            raise serializers.ValidationError(
                "Amount is below minimum lock_side threshold.")

        if amount > getattr(company_permission, max_amount_fld):
            raise serializers.ValidationError(
                "Amount is above maximum lock_side threshold.")

    return ret


# ===========

def shared_payment_validation(attrs):
    if attrs['action'] == Ticket.Actions.RFQ:
        raise serializers.ValidationError(
            "There is no RFQ for same currency transactions. Use execute to transfer money.")

    # pop off open date from attrs
    open_date = attrs.pop('open_date', None)

    # this is same currency payment stuff
    attrs['tenor'] = Ticket.Tenors.SPOT
    attrs['market_name'] = attrs.get('sell_currency').get_mnemonic(
    ) + attrs.get('buy_currency').get_mnemonic()
    attrs['instrument_type'] = Ticket.Tenors.SPOT
    attrs['destination'] = 'CORPAY'
    attrs['rfq_type'] = CnyExecution.RfqTypes.API
    attrs['execution_strategy'] = Ticket.ExecutionStrategies.MARKET

    # legacy support?
    if not attrs.get('side', None):
        attrs['side'] = 'Buy'

    mkt = attrs.get('market_name', None)

    ref = get_reference_data(mkt)
    if not ref:
        raise serializers.ValidationError(
            "This market is not configured. Please contact support.")

    # round amount
    # round any rates
    is_ndf = (ref['CCY_TYPE'] == 'NDF')
    exec_cfg = pangea_client.get_exec_config(
        market_name=attrs['market_name'], company=attrs['company'].id)

    if not exec_cfg:
        raise serializers.ValidationError(
            "This market is not configured for execution. Please contact support.")

    if not exec_cfg['active']:
        raise serializers.ValidationError(
            "This market is not active. Please contact support.")

    # ===================================

    start = attrs.get('start_time')
    end = attrs.get('end_time')

    if end and end < datetime.utcnow():
        raise serializers.ValidationError(
            "End time cannot be in the past. Make sure you are using UTC.")
    elif start and end and start > end:
        raise serializers.ValidationError(
            "End time cannot be greater than start time. Make sure you are using UTC.")

    # ===================================
    basic = None
    if basic:
        return

    tz = pytz.timezone('America/New_York')
    tdy = datetime.now(tz).date()

    start_time = attrs.get('start_time', datetime.utcnow())  # in utc
    spot_date, valid_days, spot_days = get_spot_dt(
        attrs['market_name'], ref_dt=start_time)

    logger.info(
        f'input value_date: {attrs["value_date"]} spot_date: {spot_date}')

    if isinstance(attrs['value_date'], str):
        if attrs['value_date'] == 'SPOT':
            # TODO: set start_time to future liquid fix time to
            attrs['tenor'] = Ticket.Tenors.SPOT
            attrs['instrument_type'] = Ticket.Tenors.SPOT
            attrs['value_date'] = spot_date
        elif attrs['value_date'] == 'RTP':
            attrs['tenor'] = Ticket.Tenors.RTP  # overnight
            attrs['instrument_type'] = Ticket.Tenors.SPOT
            attrs['value_date'] = start_time.date()
        elif attrs['value_date'] == 'EOD':
            attrs['tenor'] = Ticket.Tenors.ON  # overnight
            attrs['instrument_type'] = Ticket.Tenors.SPOT
            attrs['value_date'] = start_time.date()
        elif attrs['value_date'] == 'TOM':
            attrs['tenor'] = Ticket.Tenors.TN  # tom next
            attrs['instrument_type'] = Ticket.Tenors.SPOT
            tom_date_ind = valid_days.index_gt(spot_date)
            attrs['value_date'] = valid_days[tom_date_ind]  # +1 bday
        elif attrs['value_date'] == 'EOM':
            # if its a forward figure out the fixing date
            info = get_fx_settlement_info(attrs['market_name'], dt=datetime.utcnow(), tenor='EOM1',
                                          include_fix_date=True)
            attrs['value_date'] = info['settle_date']
            if is_ndf:
                attrs['fixing_date'] = info['fixing_date']
                attrs['fixing_time'] = ref.get('FIXING_TIME', None)
                attrs['fixing_venue'] = ref.get('FIXING_VENUE', None)
                attrs['fixing_source'] = ref.get('FIXING_SRC', None)
                attrs['tenor'] = Ticket.Tenors.FWD
                attrs['instrument_type'] = Ticket.Tenors.NDF
            else:
                attrs['tenor'] = Ticket.Tenors.FWD
                attrs['instrument_type'] = Ticket.Tenors.FWD
        else:
            raise serializers.ValidationError(
                f"value_date can only be SPOT, RTP, EOD, TOM, EOM or a date.")

    # this is also wrong as the date should be NYC 5PM
    # TODO: this is in local time so thats kinda fucked up
    elif attrs['value_date'] < tdy:
        raise serializers.ValidationError(
            f"value_date must be >= today ({attrs['value_date'].isoformat()} < {tdy.isoformat()})")
    elif attrs['value_date'] <= spot_date:
        # TODO: note what to do based on RTP
        attrs['tenor'] = Ticket.Tenors.SPOT
        attrs['instrument_type'] = Ticket.Tenors.SPOT
        attrs['value_date'] = spot_date  # to be safe
    else:
        # NOTE: check that forward value date is valid. if it isn't, use the convention to fix it or error.

        valid_value_date = infer_valid_settlement_day(attrs['market_name'], attrs['value_date'],
                                                      rule=attrs['date_conversion'])

        if not valid_value_date or valid_value_date < tdy:
            raise serializers.ValidationError(
                f"Invalid value_date provided ({attrs['value_date'].isoformat()})")

        attrs['value_date'] = valid_value_date
        attrs['instrument_type'] = Ticket.Tenors.SPOT
        evaluate_scheduled_spot(attrs)

    # =================

    route_ticket(attrs, exec_cfg)

    settle_account_id = attrs.pop('settle_account_id', None)
    beneficiary_id = attrs.pop('beneficiary_id', None)

    # todo, use these to set up bene and settlement accounts here

    start = attrs.get('start_time')
    scheduled = start and start > datetime.utcnow()

    # PUT DEFAULT SETTLEMENT INFORMATION IN HERE??
    # TODO: always have defaults so this isn't an issue

    if not scheduled:
        shared_ticket_bene_validation(attrs)


# =============================

def shared_conversion_validation(attrs, basic=False):
    if 'market_name' not in attrs or not attrs['market_name']:
        fxpair, side = determine_rate_side(
            attrs.get('sell_currency'), attrs.get('buy_currency'))
        # print( fxpair.market, side )
        # fxpair = FxPair.get_pair_from_currency(attrs.get('sell_currency'),attrs.get('buy_currency'))
        attrs['market_name'] = fxpair.market
        attrs['fxpair'] = fxpair
        attrs['side'] = side
    else:
        fxpair = FxPair.get_pair_from_currency(
            attrs.get('sell_currency'), attrs.get('buy_currency'))
        attrs['market_name'] = fxpair.market

    # legacy support?
    if not attrs.get('side', None):
        attrs['side'] = 'Buy'

    mkt = attrs.get('market_name', None)

    ref = get_reference_data(mkt)
    if not ref:
        raise serializers.ValidationError(
            "This market is not configured. Please contact support.")

    # round amount
    # round any rates

    # do we want to note if its an NDF
    is_ndf = (ref['CCY_TYPE'] == 'NDF')
    open_date = attrs.pop('open_date', None)

    if open_date:
        # ensure open date is > today or sometime in teh future
        attrs['instrument_fields'] = {'open_date': open_date}

    exec_cfg = pangea_client.get_exec_config(
        market_name=attrs['market_name'], company=attrs['company'].id)

    if not exec_cfg:
        raise serializers.ValidationError(
            "This market is not configured for execution. Please contact support.")

    if not exec_cfg['active']:
        raise serializers.ValidationError(
            "This market is not active. Please contact support.")

    # ===================================

    start = attrs.get('start_time')
    end = attrs.get('end_time')

    if end and end < datetime.utcnow():
        raise serializers.ValidationError(
            "End time cannot be in the past. Make sure you are using UTC.")
    elif start and end and start > end:
        raise serializers.ValidationError(
            "End time cannot be greater than start time. Make sure you are using UTC.")

    # ===================================

    if basic:
        return

    # get all pertinent information from the exec_cfg
    # ===============================================

    tz = pytz.timezone('America/New_York')
    tdy = datetime.now(tz).date()

    start_time = attrs.get('start_time', datetime.utcnow())  # in utc
    spot_date, valid_days, spot_days = get_spot_dt(
        attrs['market_name'], ref_dt=start_time)

    if isinstance(attrs['value_date'], str):
        if attrs['value_date'] == 'SPOT':
            # TODO: set start_time to future liquid fix time to
            attrs['tenor'] = Ticket.Tenors.SPOT
            attrs['instrument_type'] = Ticket.Tenors.SPOT
            attrs['value_date'] = spot_date
        elif attrs['value_date'] == 'RTP':
            attrs['tenor'] = Ticket.Tenors.RTP  # overnight
            attrs['instrument_type'] = Ticket.Tenors.SPOT
            attrs['value_date'] = start_time.date()
        elif attrs['value_date'] == 'EOD':
            attrs['tenor'] = Ticket.Tenors.ON  # overnight
            attrs['instrument_type'] = Ticket.Tenors.SPOT
            attrs['value_date'] = start_time.date()
        elif attrs['value_date'] == 'TOM':
            attrs['tenor'] = Ticket.Tenors.TN  # tom next
            attrs['instrument_type'] = Ticket.Tenors.SPOT
            tom_date_ind = valid_days.index_gt(spot_date)
            attrs['value_date'] = valid_days[tom_date_ind]  # +1 bday
        elif attrs['value_date'] == 'EOM':
            # if its a forward figure out the fixing date
            info = get_fx_settlement_info(attrs['market_name'], dt=datetime.utcnow(), tenor='EOM1',
                                          include_fix_date=True)
            attrs['value_date'] = info['settle_date']
            if is_ndf:
                attrs['fixing_date'] = info['fixing_date']
                attrs['fixing_time'] = ref.get('FIXING_TIME', None)
                attrs['fixing_venue'] = ref.get('FIXING_VENUE', None)
                attrs['fixing_source'] = ref.get('FIXING_SRC', None)
                attrs['tenor'] = Ticket.Tenors.FWD
                attrs['instrument_type'] = Ticket.Tenors.NDF
            else:
                attrs['tenor'] = Ticket.Tenors.FWD
                attrs['instrument_type'] = Ticket.Tenors.FWD
        else:
            raise serializers.ValidationError(
                f"value_date can only be SPOT, RTP, EOD, TOM, EOM or a date.")

    # this is also wrong as the date should be NYC 5PM
    # TODO: this is in local time so thats kinda fucked up
    elif attrs['value_date'] < tdy:
        raise serializers.ValidationError(
            f"value_date must be >= today ({attrs['value_date'].isoformat()} < {tdy.isoformat()})")
    elif attrs['value_date'] <= spot_date:
        # TODO: note what to do based on RTP
        attrs['tenor'] = Ticket.Tenors.SPOT
        attrs['instrument_type'] = Ticket.Tenors.SPOT
        attrs['value_date'] = spot_date  # to be safe
    else:
        # NOTE: check that forward value date is valid. if it isn't, use the convention to fix it or error.

        valid_value_date = infer_valid_settlement_day(attrs['market_name'], attrs['value_date'],
                                                      rule=attrs['date_conversion'])

        if not valid_value_date or valid_value_date < tdy:
            raise serializers.ValidationError(
                f"Invalid value_date provided ({attrs['value_date'].isoformat()})")

        attrs['value_date'] = valid_value_date

        if attrs.get('tenor') in (Ticket.Tenors.SPOT, Ticket.Tenors.RTP, Ticket.Tenors.ON, Ticket.Tenors.TN):
            # TODO: make sure you have broker support for this
            # this is a scheduled spot transaction
            attrs['instrument_type'] = Ticket.Tenors.SPOT
            evaluate_scheduled_spot(attrs)
        else:
            # TODO: depending on start_time, this may not be a forward?
            if open_date:
                attrs['tenor'] = Ticket.Tenors.FWD
                attrs['instrument_type'] = Ticket.InstrumentTypes.WINDOW_FWD
            elif is_ndf:
                attrs['tenor'] = Ticket.Tenors.FWD
                attrs['instrument_type'] = Ticket.Tenors.NDF
                if 'fixing_date' not in attrs or not attrs['fixing_date']:
                    attrs['fixing_date'] = get_fx_fixing_dt(
                        attrs['market_name'], attrs['value_date'])
                attrs['fixing_time'] = ref.get('FIXING_TIME', None)
                attrs['fixing_venue'] = ref.get('FIXING_VENUE', None)
                attrs['fixing_source'] = ref.get('FIXING_SRC', None)
            else:
                attrs['tenor'] = Ticket.Tenors.FWD
                attrs['instrument_type'] = Ticket.Tenors.FWD

    route_ticket(attrs, exec_cfg)

    settle_account_id = attrs.pop('settle_account_id', None)
    beneficiary_id = attrs.pop('beneficiary_id', None)

    # todo, use these to set up bene and settlement accounts here

    start = attrs.get('start_time')
    scheduled = start and start > datetime.utcnow()

    # PUT DEFAULT SETTLEMENT INFORMATION IN HERE??
    # TODO: always have defaults so this isn't an issue

    if not scheduled:
        shared_ticket_bene_validation(attrs)

    # TODO:
    # if you are a spot transaction going to corpay for this FxPair and client is eligible for mass payments,
    # validate the beneficiary object... that all the necessary fields are filled out.
    # do not indicate to the customer in any way that this is corpay specific. even if we collect information
    # that corpay doesn't need or use.

    # ==========

    if not exec_cfg['use_triggers']:
        if attrs['limit_trigger'] or attrs['stop_trigger'] or attrs['upper_trigger'] or attrs['lower_trigger']:
            # print WARN: triggers are ignored
            pass
    if attrs['execution_strategy'] == Ticket.ExecutionStrategies.BESTX:
        evaluate_best_ex(attrs)
    elif attrs['execution_strategy'] == Ticket.ExecutionStrategies.SMART:
        evaluate_smart_ex(attrs)
    elif attrs['execution_strategy'] == Ticket.ExecutionStrategies.LIMIT and attrs['limit_trigger']:
        raise serializers.ValidationError(
            "Must provide limit_trigger if using execution_strategy: LIMIT")
    elif attrs['execution_strategy'] == Ticket.ExecutionStrategies.STOP and attrs['stop_trigger'] is None:
        raise serializers.ValidationError(
            "Must provide stop_trigger if using execution_strategy: STOP")
    elif attrs['execution_strategy'] == Ticket.ExecutionStrategies.TRIGGER and attrs[
            'upper_trigger'] is None and \
            attrs['lower_trigger'] is None and attrs['trigger_time'] is None:
        raise serializers.ValidationError(
            "Must provide at least one trigger if using execution_strategy: TRIGGER")

    trigger_time = attrs.get('trigger_time')
    start_time = attrs.get('start_time')

    if trigger_time and start_time and trigger_time < start_time:
        raise serializers.ValidationError("trigger_time is before start_time")
        # TODO: do we want to set end_time to expire the execution???

    if attrs['action'] == Ticket.Actions.RFQ:
        if not attrs.get('end_time'):
            start = attrs.get('start_time')
            if not start:
                start = datetime.utcnow()
            attrs['end_time'] = start + timedelta(days=1)


def shared_ticket_validation(attrs, basic=False):
    if attrs.get('sell_currency') == attrs.get('buy_currency'):
        shared_payment_validation(attrs)
    else:
        shared_conversion_validation(attrs, basic=basic)
    return attrs
