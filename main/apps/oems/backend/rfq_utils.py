import abc
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, Type

from django.conf import settings

from main.apps.account.models import Company
from main.apps.broker.models import CurrencyFee, Broker
from main.apps.corpay.models import CorpaySettings, Locksides
from main.apps.corpay.services.api.dataclasses.forwards import RequestForwardQuoteBody, CompleteOrderBody, \
    DrawdownOrder, DrawdownPaymentFee, DrawdownPayment, DrawdownBody, DrawdownSettlement
from main.apps.corpay.services.api.dataclasses.mass_payment import QuotePayment, QuotePaymentsBody, BookPaymentsParams, \
    BookPaymentsBody
from main.apps.corpay.services.api.dataclasses.spot import InstructDealBody, InstructDealSettlement, InstructDealOrder, \
    InstructDealPayment
from main.apps.corpay.services.api.dataclasses.spot import SpotRateBody
from main.apps.corpay.services.corpay import CorPayExecutionServiceFactory, CorPayExecutionService
from main.apps.currency.models import Currency
from main.apps.marketdata.services.initial_marketdata import get_recent_spot_rate, get_initial_market_state
from main.apps.nium.services.api.dataclasses.payout import (
    BeneficiaryDetail,
    Payout,
    PurposeCode,
    SourceOfFunds,
    TransferMoneyPayload,
    TransferMoneyResponse
)
from main.apps.oems.backend.date_utils import now, add_time
from main.apps.oems.backend.date_utils import parse_datetime
from main.apps.oems.backend.states import INTERNAL_STATES, EXTERNAL_STATES
from main.apps.oems.models import CnyExecution
from main.apps.oems.models.ticket import Ticket
from main.apps.settlement.models import Wallet, BeneficiaryBroker, Beneficiary
from main.apps.settlement.services.beneficiary import CorpayBeneficiaryService

# ===========

logger = logging.getLogger(__name__)


def calculate_external_quote(rate, ticket):
    if True:  # TODO: we don't have managed pricing like this yet
        secs = 9
        mult = 1.0
    elif ticket.time_in_force == '1min':
        secs = 60
        mult = 0.99
    elif ticket.time_in_force == '10s':
        secs = 10
        mult = 1.0
    elif ticket.time_in_force == '1hr':
        secs = 3600
        mult = 0.98
    else:
        # TODO: for non-rfq orders, we don't want to expire them ever
        # thus we will not want to expire them.
        # if ticket.time_in_force == 'gtc':
        secs = 3600
        mult = 0.98

    ticket.external_quote_id = str(uuid.uuid4())
    ticket.external_quote = rate * mult if mult != 1.0 else rate
    ticket.external_quote_expiry = add_time(now(), seconds=secs)

    return ticket


# ===========

class RfqInterface(abc.ABC):
    broker_interfaces: Dict[str, Type["RfqInterface"]] = {}

    @classmethod
    def register(cls, interface, key=None):
        key = key or interface.broker
        cls.broker_interfaces[key] = interface

    @classmethod
    def do_api_rfq(cls, ticket, *args, **kwargs):

        if settings.OEMS_NO_TRADING:
            raise RuntimeError(
                "OEMS_NO_TRADING FLAG SET. YOU SHOULD NOT BE TRADING!!! SHAME!!!")

        broker = ticket.broker
        ticket.transaction_time = now()

        if broker in cls.broker_interfaces:
            return cls.broker_interfaces[broker].rfq(ticket, *args, **kwargs)
        else:
            # no broker interface found
            raise NotImplementedError(
                'No broker interface found for ' + broker)

    @classmethod
    def do_indicative_rfq(cls, ticket, *args, internal_only=False, **kwargs):

        if settings.OEMS_NO_TRADING:
            raise RuntimeError(
                "OEMS_NO_TRADING FLAG SET. YOU SHOULD NOT BE TRADING!!! SHAME!!!")

        buy_currency = ticket.get_buy_currency()
        sell_currency = ticket.get_sell_currency()

        data = get_initial_market_state(
            sell_currency, buy_currency, tenor=ticket.value_date)

        ticket.transaction_time = now()

        # TODO: add fees in
        if data and data.get('rate') is not None:

            rate = data['rate']
            spot_rate = data['spot_rate']
            fwd_points = data['fwd_points']

            if False and ticket.side == 'Sell':
                rate = 1.0 / rate
                sr = 1.0 / spot_rate
                fwd_points = (rate - sr)

            ticket.quote_fee = 0.0
            ticket.quote_source = 'indicative'
            ticket.quote_indicative = True
            ticket.internal_quote_id = str(uuid.uuid4())
            ticket.internal_quote = rate  # which way for testing
            ticket.internal_quote_info = data
            ticket.internal_quote_expiry = add_time(now(), seconds=19)

            if not internal_only:
                # calculate the modified quote
                cls.calculate_external_quote(
                    cls, ticket.internal_quote, ticket)

            ticket.change_internal_state(INTERNAL_STATES.RFQ_DONE)
            if ticket.action == Ticket.Actions.RFQ:
                ticket.change_external_state(EXTERNAL_STATES.DONE)

            ticket.spot_rate = spot_rate
            ticket.fwd_points = fwd_points
            ticket.fee = 0.0  # put the fee in here

            return True
        else:
            return False

    @classmethod
    def do_api_execute(cls, ticket, *args, **kwargs):

        if settings.OEMS_NO_TRADING:
            raise RuntimeError(
                "OEMS_NO_TRADING FLAG SET. YOU SHOULD NOT BE TRADING!!! SHAME!!!")

        broker = ticket.broker
        ticket.transaction_time = now()

        if broker in cls.broker_interfaces:
            return cls.broker_interfaces[broker].execute(ticket, *args, **kwargs)
        else:
            # no broker interface found
            raise NotImplementedError(
                'No broker interface found for ' + broker)

    @classmethod
    def do_api_complete(cls, ticket, *args, **kwargs):

        if settings.OEMS_NO_TRADING:
            raise RuntimeError(
                "OEMS_NO_TRADING FLAG SET. YOU SHOULD NOT BE TRADING!!! SHAME!!!")

        broker = ticket.broker

        if broker in cls.broker_interfaces:
            return cls.broker_interfaces[broker].complete(ticket, *args, **kwargs)
        else:
            # no broker interface found
            raise NotImplementedError(
                'No broker interface found for ' + broker)

    @classmethod
    def do_api_settle(cls, ticket, *args, **kwargs):

        if settings.OEMS_NO_TRADING:
            raise RuntimeError(
                "OEMS_NO_TRADING FLAG SET. YOU SHOULD NOT BE TRADING!!! SHAME!!!")

        broker = ticket.broker

        if broker in cls.broker_interfaces:
            return cls.broker_interfaces[broker].settle(ticket, *args, **kwargs)
        else:
            # no broker interface found
            raise NotImplementedError(
                'No broker interface found for ' + broker)

    @classmethod
    def do_api_inspect(cls, ticket, *args, **kwargs):
        broker = ticket.broker
        if broker in cls.broker_interfaces:
            return cls.broker_interfaces[broker].inspect(ticket, *args, **kwargs)
        else:
            # no broker interface found
            raise NotImplementedError(
                'No broker interface found for ' + broker)

    @classmethod
    def do_api_tts(cls, ticket, *args, **kwargs):
        broker = ticket.broker
        if broker in cls.broker_interfaces:
            return cls.broker_interfaces[broker].time_to_settle(ticket, *args, **kwargs)
        else:
            # no broker interface found
            raise NotImplementedError(
                'No broker interface found for ' + broker)

    @classmethod
    def do_pre_exec_check(cls, ticket, *args, **kwargs):
        broker = ticket.broker
        if broker in cls.broker_interfaces:
            return cls.broker_interfaces[broker].pre_exec_check(ticket, *args, **kwargs)
        else:
            # no broker interface found
            raise NotImplementedError(
                'No broker interface found for ' + broker)

    # ===========================

    def calculate_external_quote(self, rate, ticket):

        # we cannot do managed pricing or hold rates yet
        secs = 9
        mult = 1.0

        ticket.external_quote_id = str(uuid.uuid4())
        ticket.external_quote = rate * mult if mult != 1.0 else rate
        ticket.external_quote_expiry = add_time(now(), seconds=secs)

        return ticket

    # ===========================

    def rate(self, ticket, *args, **kwargs):
        pass  # THIS IS TO GET AN INDICATIVE RATE. CALL HELPER FOR NO TICKET

    def rfq(self, ticket, *args, **kwargs):
        pass

    def execute(self, ticket, *args, **kwargs):
        pass

    def complete(self, ticket, *args, **kwargs):
        pass

    def settle(self, ticket, *args, **kwargs):
        pass

    def inspect(self, ticket, *args, **kwargs):
        ...

    def time_to_settle(self, ticket, *args, **kwargs):
        ...

    def pre_exec_check(self, ticket, *args, **kwargs):
        return False  # cannot execute anything by default


# ============================================

def get_corpay_drawdown_data(ticket: Ticket, broker: Broker, corpay_api: CorPayExecutionService):
    spot_response = get_mp_spot_rate(ticket, ticket.company, corpay_api)
    fees = calculate_mp_fee(
        spot_response=spot_response,
        buy_currency=ticket.buy_currency.mnemonic,
        sell_currency=ticket.sell_currency.mnemonic,
        lock_side=ticket.lock_side.mnemonic,
        amount=ticket.amount,
        broker=broker,
    )
    drawdown_order = DrawdownOrder(
        orderId=ticket.trade_details['ordNum'],
        amount=ticket.amount
    )
    drawdown_fee = DrawdownPaymentFee(
        expectataion='ExactFee',
        amount=fees['fee_amount_usd'],
        currency='USD'
    )
    drawdown_payments = []

    for beneficiary in ticket.beneficiaries:
        drawdown_payments.append(
            DrawdownPayment(
                beneficiaryId=beneficiary['beneficiary_id'],
                deliveryMethod=beneficiary['method'],
                amount=ticket.amount,
                currency=ticket.buy_currency.mnemonic,
                purposeOfPayment=beneficiary['purpose_of_payment'],
                fee=drawdown_fee
            )
        )
    drawdown_settlements = []
    for settlement_info in ticket.settlement_info:
        drawdown_settlements.append(
            DrawdownSettlement(
                accountId=settlement_info['settlement_account_id'],
                deliveryMethod=settlement_info['method'],
                currency=ticket.sell_currency.mnemonic,
                purpose='Drawdown'
            )
        )
    drawdown_body = DrawdownBody(
        orders=[
            drawdown_order
        ],
        payments=drawdown_payments,
        settlements=drawdown_settlements
    )
    return drawdown_body


def calculate_corpay_fee(buy_currency: str, sell_currency: str, broker: Broker, method='max'):
    fees = CurrencyFee.get_fees(
        currencies=[
            sell_currency,
            buy_currency
        ],
        broker=broker
    )
    if method == 'max':
        return max(fees, key=lambda x: x.pangea_fee)
    else:
        raise NotImplementedError
    return fees


def calculate_mp_fee(spot_response: dict, buy_currency: str, sell_currency: str, lock_side: str, amount: float,
                     broker: Broker):
    fee = CurrencyFee.get_max(
        currencies=[
            sell_currency,
            buy_currency
        ],
        broker=broker
    )

    conversion_rate = spot_response[0]['rate']
    sell_currency_usd_rate = spot_response[-1]['rate']
    settlement_amount = spot_response[0]['settlementAmount']
    amount_total = spot_response[0]['amountTotal']

    if True:  # new methodology

        # TODO: this can get reduced to 2 branches just
        # nice to see the cases.

        if sell_currency == 'USD':

            if lock_side == buy_currency:

                usd_amount = amount * conversion_rate
                fee_amount = usd_amount * fee

                fees = {
                    "fee_amount": fee_amount,
                    "fee_unit": sell_currency,
                    "fee": fee,
                    "payment_amount": amount,
                    "from": sell_currency,
                    "to": buy_currency,
                    "lock_side": lock_side,
                }

            elif lock_side == sell_currency:

                fee_amount = amount * fee
                payment_amount = (amount - fee_amount)

                fees = {
                    "fee_amount": fee_amount,
                    "fee_unit": sell_currency,
                    "fee": fee,
                    "payment_amount": payment_amount,
                    "from": sell_currency,
                    "to": buy_currency,
                    "lock_side": lock_side,
                }

        elif buy_currency == 'USD':

            if lock_side == buy_currency:

                # sell EUR buy 10,000 USD
                non_usd_amount = amount / conversion_rate
                fee_amount = non_usd_amount * fee

                fees = {
                    "fee_amount": fee_amount,
                    "fee_unit": sell_currency,
                    "fee": fee,
                    "payment_amount": amount,
                    "from": sell_currency,
                    "to": buy_currency,
                    "lock_side": lock_side,
                }

                # convert X EUR to 100,000 USD
                # send 93356.73 EUR to USD
                # draft 466.78 EUR to our wallet

                # print( fees )
                # print( conversion_rate, sell_currency_usd_rate )
                # print( settlement_amount, amount_total )

                # breakpoint()

            elif lock_side == sell_currency:

                # sell 10,000 EUR buy USD
                fee_amount = amount * fee
                payment_amount = (amount - fee_amount)

                fees = {
                    "fee_amount": fee_amount,
                    "fee_unit": sell_currency,
                    "fee": fee,
                    "payment_amount": payment_amount,
                    "from": sell_currency,
                    "to": buy_currency,
                    "lock_side": lock_side,
                }

        else:

            if lock_side == buy_currency:

                # sell EUR buy 100,000 CAD
                non_usd_amount = amount / conversion_rate
                fee_amount = non_usd_amount * fee

                fees = {
                    "fee_amount": fee_amount,
                    "fee_unit": sell_currency,
                    "fee": fee,
                    "payment_amount": amount,
                    "from": sell_currency,
                    "to": buy_currency,
                    "lock_side": lock_side,
                }

                # convert X EUR to 100,000 USD
                # send 93356.73 EUR to USD
                # draft 466.78 EUR to our wallet

                # print( fees )
                # print( conversion_rate, sell_currency_usd_rate )
                # print( settlement_amount, amount_total )

                # breakpoint()

            elif lock_side == sell_currency:

                # sell 10,000 EUR buy USD
                fee_amount = amount * fee
                payment_amount = (amount - fee_amount)

                fees = {
                    "fee_amount": fee_amount,
                    "fee_unit": sell_currency,
                    "fee": fee,
                    "payment_amount": payment_amount,
                    "from": sell_currency,
                    "to": buy_currency,
                    "lock_side": lock_side,
                }

        return fees

    if sell_currency == 'USD':
        fee_amount_usd = amount * fee
    elif buy_currency == 'USD':
        if lock_side != 'USD':
            fee_amount_usd = amount * conversion_rate * fee
        else:
            fee_amount_usd = amount_total * fee
    else:
        fee_amount_usd = amount * fee / sell_currency_usd_rate

    if lock_side == buy_currency:
        settlement_amount += fee_amount_usd * sell_currency_usd_rate
    elif lock_side == sell_currency:
        amount_total = (amount - fee_amount_usd * sell_currency_usd_rate)

    fees = {
        "fee_amount_usd": fee_amount_usd,
        "value": settlement_amount / amount_total,
        "fee": fee,
        "amount_settlement": settlement_amount,
        "amount_total": amount_total,
    }

    return fees


def get_mp_spot_rate(ticket: Ticket, company: Company, corpay_api, remitter_id=None, payment_id=None):
    cp_settings = CorpaySettings.get_settings(company)
    beneficiary = ticket.beneficiaries[0]
    settlement_info = ticket.settlement_info[0]
    method_map = {
        'W': 'Wire',
        'E': 'EFT',
        'C': 'StoredValue'
    }
    settlement_method_key = settlement_info['method'].upper()
    beneficiary_method_key = beneficiary['method'].upper()
    if settlement_method_key in method_map:
        settlement_info['method'] = method_map[settlement_method_key]
    if beneficiary_method_key in method_map:
        beneficiary['method'] = method_map[beneficiary_method_key]
    payments_payload = []
    payment = QuotePayment(
        beneficiaryId=beneficiary['beneficiary_id'],
        paymentMethod=beneficiary['method'],
        purposeOfPayment=beneficiary['purpose_of_payment'],
        amount=ticket.amount,
        lockside=ticket.get_corpay_lock_side(),
        paymentCurrency=ticket.buy_currency.mnemonic,
        settlementCurrency=ticket.sell_currency.mnemonic,
        settlementMethod=settlement_info['method'],
        settlementAccountId=settlement_info['settlement_account_id'],
        paymentReference=settlement_info['payment_reference'],
        remitterId=remitter_id,
        deliveryDate=ticket.value_date.strftime('%Y-%m-%d'),
        paymentId=payment_id
    )
    payments_payload.append(payment)
    if ticket.buy_currency.mnemonic != 'USD':
        usd_fee_payment = QuotePayment(
            beneficiaryId=cp_settings.fee_wallet_id,
            paymentMethod='StoredValue',
            amount=100,
            lockside=Locksides.Settlement.value,
            paymentCurrency='USD',
            settlementCurrency=ticket.sell_currency.mnemonic,
            settlementAccountId=settlement_info['settlement_account_id'],
            settlementMethod=settlement_info['method'],
            purposeOfPayment='PROFESSIONAL FEES PAYMENT',
            paymentReference='Pangea Spot Transaction Fee'
        )
        payments_payload.append(usd_fee_payment)
    data = QuotePaymentsBody(payments=payments_payload)
    response = corpay_api.quote_payments(data=data)
    return response['paymentSummary']


def get_mp_data(ticket: Ticket, fee, company: Company, remitter_id=None, payment_id=None):
    cp_settings = CorpaySettings.get_settings(company)
    beneficiary = ticket.beneficiaries[0]
    settlement_info = ticket.settlement_info[0]
    method_map = {
        'W': 'Wire',
        'E': 'EFT',
        'C': 'StoredValue'
    }
    if settlement_info['method'].upper() in method_map:
        settlement_info['method'] = method_map[settlement_info['method'].upper()]
    if beneficiary['method'].upper() in method_map:
        beneficiary['method'] = method_map[beneficiary['method'].upper()]

    original_payment = QuotePayment(
        beneficiaryId=beneficiary['beneficiary_id'],
        paymentMethod=beneficiary['method'],
        purposeOfPayment=beneficiary['purpose_of_payment'],
        amount=fee['payment_amount'],
        lockside=ticket.get_corpay_lock_side(),
        paymentCurrency=fee['to'],
        settlementCurrency=fee['from'],
        settlementMethod=settlement_info['method'],
        settlementAccountId=settlement_info['settlement_account_id'],
        paymentReference=settlement_info['payment_reference'],
        remitterId=remitter_id,
        deliveryDate=ticket.value_date.strftime('%Y-%m-%d'),
        paymentId=payment_id
    )
    pangea_fee_payment = QuotePayment(
        beneficiaryId=cp_settings.fee_wallet_id,
        paymentMethod='StoredValue',
        amount=fee['fee_amount'],
        lockside=Locksides.Settlement.value,
        paymentCurrency='USD',
        settlementCurrency=fee['fee_unit'],
        settlementAccountId=settlement_info['settlement_account_id'],
        settlementMethod=settlement_info['method'],
        purposeOfPayment='PROFESSIONAL FEES PAYMENT',
        paymentReference='Pangea Spot Transaction Fee'
    )
    data = QuotePaymentsBody(payments=[
        original_payment,
        pangea_fee_payment
    ])
    return data


class CorpayInterface(RfqInterface):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.broker = 'CORPAY'
        self._broker_model = None

    @property
    def broker_model(self) -> str:
        if not self._broker_model:
            self._broker_model = Broker.objects.get(name='Corpay')
        return self._broker_model

    def get_fees(self, buy_currency: str, sell_currency: str):
        return calculate_corpay_fee(buy_currency, sell_currency, self.broker_model)

    def calculate_external_quote(self, rate, ticket):

        # we cannot do managed pricing or hold rates yet
        secs = 10
        mult = 1.0

        ticket.external_quote_id = str(uuid.uuid4())
        ticket.external_quote = rate * mult if mult != 1.0 else rate
        ticket.external_quote_expiry = add_time(now(), seconds=secs)

        return ticket

    def mass_payment_rfq(self, ticket, *args, internal_only=False, delivery_fee=0.0, delivery_fee_unit='USD',
                         **kwargs):

        corpay_api = CorPayExecutionServiceFactory.for_company(
            ticket.get_company())
        payments_payload = []

        if len(ticket.settlement_info) > 1:
            raise NotImplementedError

        settlement_info = ticket.settlement_info[0]
        settle_method = self.mp_method_map.get(
            settlement_info['method'], settlement_info['method'])

        cp_lockside = ticket.get_corpay_lock_side()
        buy_currency = ticket.get_buy_currency()
        sell_currency = ticket.get_sell_currency()

        for beneficiary in ticket.beneficiaries:
            method = self.mp_method_map.get(
                beneficiary['method'], beneficiary['method'])

            payment = QuotePayment(
                beneficiaryId=beneficiary['beneficiary_id'],
                paymentMethod=method,
                purposeOfPayment=beneficiary['purpose_of_payment'],
                amount=beneficiary['amount'],
                lockside=cp_lockside,
                paymentCurrency=buy_currency.mnemonic,
                settlementCurrency=sell_currency.mnemonic,
                settlementMethod=settle_method,
                settlementAccountId=settlement_info['settlement_account_id'],
                paymentReference=settlement_info['payment_reference'],
                remitterId=beneficiary.get('remitter_id'),
                deliveryDate=ticket.value_date.strftime('%Y-%m-%d'),
                paymentId=beneficiary.get('payment_id'),
            )
            payments_payload.append(payment)

        if delivery_fee and delivery_fee_unit:

            if delivery_fee_unit != 'USD':
                raise NotImplementedError

            cp_settings = CorpaySettings.get_settings(ticket.get_company())
            # TODO: make sure this is USD

            usd_fee_payment = QuotePayment(
                beneficiaryId=cp_settings.fee_wallet_id,
                paymentMethod='StoredValue',
                amount=delivery_fee,
                lockside=Locksides.Settlement.value,
                paymentCurrency=delivery_fee_unit,
                settlementCurrency=delivery_fee_unit,
                settlementAccountId=settlement_info['settlement_account_id'],
                settlementMethod=settle_method,
                purposeOfPayment='PROFESSIONAL FEES PAYMENT',
                paymentReference='Pangea Spot Transaction Fee'
            )
            payments_payload.append(usd_fee_payment)

        # =======================

        payload = QuotePaymentsBody(payments=payments_payload)
        data = corpay_api.quote_payments(data=payload)

        if not data:
            raise ValueError

        for row in data['paymentSummary']:
            buy_ccy = row['paymentCurrency']
            sell_ccy = row['settlementCurrency']
            if buy_ccy == buy_currency.mnemonic and sell_ccy == sell_currency.mnemonic:
                rate = row['rate']
                break
        else:
            raise

        # done, cntr_done, all_in_rate, extra = self.mp_summarize( dj_ticket, data['paymentSummary'], data['fees'])

        ticket.quote_source = 'CORPAY_MP'  # this is how we catch in execute
        ticket.internal_quote_id = '|'.join(
            [data['quote_id'], data['session_id']])
        ticket.internal_quote = rate  # which way for testing
        ticket.internal_quote_info = data
        ticket.internal_quote_expiry = add_time(now(), seconds=19)

        if not internal_only:
            # calculate the modified quote
            self.calculate_external_quote(ticket.internal_quote, ticket)

        ticket.change_internal_state(INTERNAL_STATES.RFQ_DONE)
        if ticket.action == Ticket.Actions.RFQ:
            ticket.change_external_state(EXTERNAL_STATES.DONE)

        if buy_currency.mnemonic == sell_currency.mnemonic:
            ticket.done = ticket.cntr_done = ticket.amount
            ticket.spot_rate = 1.0
            ticket.fwd_points = 0.0
            ticket.quote_fee = 0.0
            ticket.delivery_fee = delivery_fee
            ticket.delivery_fee_unit = delivery_fee_unit
            ticket.fee = 0.0
        else:
            raise NotImplementedError

        ticket.rate = ticket.internal_quote
        ticket.all_in_rate = ticket.external_quote
        ticket.all_in_done = ticket.done
        ticket.all_in_cntr_done = ticket.cntr_done

        return True

    def rfq(self, ticket, *args, internal_only=False, **kwargs):

        lock_side = ticket.get_corpay_lock_side()
        company = ticket.get_company()
        buy_currency = ticket.get_buy_currency()
        sell_currency = ticket.get_sell_currency()

        corpay_api = CorPayExecutionServiceFactory.for_company(company)
        data = None

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:

            if buy_currency.mnemonic == sell_currency.mnemonic:

                delivery_fee, fee_unit = 0.0, 'USD'

                if delivery_fee > 0.0:

                    try:
                        return self.mass_payment_rfq(ticket, *args, internal_only=internal_only,
                                                     delivery_fee=delivery_fee, delivery_fee_unit=fee_unit, **kwargs)
                    except Exception as e:
                        logger.exception(e)
                        ticket.error_message = 'RFQ FAILED'
                        ticket.change_internal_state(INTERNAL_STATES.FAILED)
                        return False

            # ==========

            if ticket.beneficiaries and len(ticket.beneficiaries) > 1:
                try:
                    return self.mass_payment_rfq(ticket, *args, internal_only=internal_only, **kwargs)
                except Exception as e:
                    logger.exception(e)
                    ticket.error_message = 'RFQ FAILED'
                    ticket.change_internal_state(INTERNAL_STATES.FAILED)
                    return False
            else:
                body = SpotRateBody(
                    paymentCurrency=buy_currency.mnemonic,
                    settlementCurrency=sell_currency.mnemonic,
                    amount=ticket.amount,
                    lockSide=lock_side
                )

                try:
                    data = corpay_api.get_spot_rate(body)
                except Exception as e:
                    logger.exception(e)

        elif ticket.instrument_type == Ticket.InstrumentTypes.FWD:

            # TODO: need to adjust the amount for MP

            # print( buy_currency.mnemonic, sell_currency.mnemonic, lock_side )
            body = RequestForwardQuoteBody(
                amount=ticket.amount,
                buyCurrency=buy_currency.mnemonic,
                forwardType='C',  # closed forward always
                lockSide=lock_side,
                maturityDate=ticket.value_date if isinstance(ticket.value_date,
                                                             str) else ticket.value_date.isoformat(),
                sellCurrency=sell_currency.mnemonic
            )

            try:
                data = corpay_api.get_forward_quote(body)
            except Exception as e:
                logger.exception(e)

        elif ticket.instrument_type == Ticket.InstrumentTypes.WINDOW_FWD:

            open_date = ticket.instrument_fields.get('open_date')
            if not open_date:
                raise ValueError('must provide open date for window forwards')

            body = RequestForwardQuoteBody(
                amount=ticket.amount,
                buyCurrency=buy_currency.mnemonic,
                forwardType='O',  # open for window forwards
                lockSide=lock_side,
                maturityDate=ticket.value_date if isinstance(ticket.value_date,
                                                             str) else ticket.value_date.isoformat(),
                sellCurrency=sell_currency.mnemonic,
                OpenDateFrom=open_date if isinstance(
                    open_date, str) else open_date.isoformat(),
            )

            try:
                data = corpay_api.get_forward_quote(body)
            except Exception as e:
                logger.exception(e)

        if data:
            # look up broker fee
            # look up pangea fee

            rate = data['rate']['value']

            if data['rate']['rateType'] != ticket.market_name:
                rate = 1.0 / rate

            # fees
            # all_in_fee = fees.broker_fee + fees.pangea_fee
            # ticket.quote_fee = all_in_fee # round(all_in_fee * (1.0-fees.rev_share),5)
            # we always show pangea fee as 0.0 in this case
            # ticket.fee = 0.0 # round(all_in_fee * fees.rev_share,5)
            # ticket.delivery_fee = fees.wire_fee

            ticket.quote_source = self.broker
            ticket.internal_quote_id = data['quoteId']
            ticket.internal_quote = rate  # which way for testing
            ticket.internal_quote_info = data
            ticket.internal_quote_expiry = add_time(now(), seconds=19)

            if not internal_only:
                # calculate the modified quote
                self.calculate_external_quote(ticket.internal_quote, ticket)

            ticket.change_internal_state(INTERNAL_STATES.RFQ_DONE)
            if ticket.action == Ticket.Actions.RFQ:
                ticket.change_external_state(EXTERNAL_STATES.DONE)

            if buy_currency.mnemonic == sell_currency.mnemonic:
                rr = 1.0
            else:
                # oer reference rate
                ref_rate = get_recent_spot_rate(ticket.market_name)
                rr = ref_rate['bid'] if ticket.side == 'Sell' else ref_rate['ask']

            # if spot rate: infer the reference rate from fees
            if ticket.instrument_type == Ticket.InstrumentTypes.FWD:

                # get a spot ref rate
                body = SpotRateBody(
                    paymentCurrency=buy_currency.mnemonic,
                    settlementCurrency=sell_currency.mnemonic,
                    amount=ticket.amount,
                    lockSide=lock_side
                )
                try:
                    spot_data = corpay_api.get_spot_rate(body)
                except Exception as e:
                    logger.exception(e)

                # corpay fee-adjusted spot rate
                spot_rate = spot_data['rate']['value']
                if spot_data['rate']['rateType'] != ticket.market_name:
                    spot_rate = 1.0 / spot_rate

                # fees
                # all_in_fee = fees.broker_fee + fees.pangea_fee
                # ticket.quote_fee = round(all_in_fee * (1.0-fees.rev_share),5)
                # ticket.fee = round(all_in_fee * fees.rev_share,5)

                """
                    if ticket.side == 'Sell':
                        ticket.spot_rate = round(spot_rate*(1.0+all_in_fee), 5)
                    else:
                        ticket.spot_rate = round(spot_rate*(1.0-all_in_fee), 5)
                """

                ticket.spot_rate = rr
                ticket.fwd_points = round(ticket.internal_quote - spot_rate, 5)
                implied_fwd_rate = rr + ticket.fwd_points

                if ticket.side == 'Sell':
                    ticket.quote_fee = round(
                        ((ticket.external_quote / implied_fwd_rate) - 1.0), 5)
                else:
                    ticket.quote_fee = round(-((implied_fwd_rate /
                                             ticket.external_quote) - 1.0), 5)

                ticket.fee = 0.0

            elif ticket.instrument_type == Ticket.InstrumentTypes.SPOT:

                ticket.spot_rate = rr
                """
                if ticket.side == 'Sell':
                    ticket.spot_rate = round(ticket.internal_quote*(1.0+all_in_fee), 5)
                else:
                    ticket.spot_rate = round(ticket.internal_quote*(1.0-all_in_fee), 5)
                """

                ticket.fwd_points = 0.0

                if ticket.side == 'Sell':
                    ticket.quote_fee = round(
                        ((ticket.external_quote / rr) - 1.0), 5)
                else:
                    ticket.quote_fee = round(-((rr /
                                             ticket.external_quote) - 1.0), 5)

                ticket.fee = 0.0

            else:
                raise NotImplementedError

            # prematurly figure this out
            pay_amount = ticket.internal_quote_info['payment']
            settle_amount = ticket.internal_quote_info['settlement']

            if settle_amount['currency'] == ticket.market_name[:3]:
                ticket.done = settle_amount['amount']
                ticket.cntr_done = pay_amount['amount']
            else:
                ticket.done = pay_amount['amount']
                ticket.cntr_done = settle_amount['amount']

            ticket.rate = ticket.internal_quote
            ticket.all_in_rate = ticket.external_quote
            ticket.all_in_done = ticket.done
            ticket.all_in_cntr_done = ticket.cntr_done

            return True

        else:
            ticket.error_message = 'RFQ FAILED'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return False

    def execute(self, ticket, *args, **kwargs):

        if hasattr(ticket, 'company'):
            company = ticket.company
        else:
            company = Company.get_company(ticket.company_id)

        corpay_api = CorPayExecutionServiceFactory.for_company(company)
        data = None

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:

            if ticket.quote_source == 'CORPAY_MP':
                quote_params = ticket.internal_quote_id.split('|')
                params = BookPaymentsParams(
                    quoteKey=quote_params[0],
                    loginSessionId=quote_params[1]
                )
                bp_data = BookPaymentsBody(
                    combineSettlements=True
                )
                data = corpay_api.book_payments(
                    params=params,
                    data=bp_data
                )
                return

            # ===========

            try:
                data = corpay_api.book_spot_deal(ticket.internal_quote_id)
            except Exception as e:
                logger.exception(e)
        elif ticket.instrument_type == Ticket.InstrumentTypes.FWD:
            try:
                data = corpay_api.book_forward_quote(ticket.internal_quote_id)
            except Exception as e:
                logger.exception(e)
        elif ticket.instrument_type == Ticket.InstrumentTypes.WINDOW_FWD:
            try:
                data = corpay_api.book_forward_quote(ticket.internal_quote_id)
            except Exception as e:
                logger.exception(e)

        if data:
            ticket.trade_details = data

            # NOTE: although forwards also return orderNumber, ignore docs bc forwardId is needed
            ticket.broker_id = data['forwardId'] if 'forwardId' in data else data['orderNumber']
            ticket.change_internal_state(INTERNAL_STATES.FILLED)

            return False
        else:
            # TODO: could go to working and try again
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return True

    def complete(self, ticket, *args, **kwargs):

        data = None

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:
            return True
        elif ticket.instrument_type == Ticket.InstrumentTypes.WINDOW_FWD or ticket.instrument_type == Ticket.InstrumentTypes.FWD:

            if ticket.rfq_type != CnyExecution.RfqTypes.API or not ticket.broker_id:
                return True

            company = ticket.get_company()
            corpay_api = CorPayExecutionServiceFactory.for_company(company)
            settlement_info = ticket.settlement_info[0]
            wallet = Wallet.objects.get(
                wallet_id=settlement_info['settlement_account_id'])
            complete_order_data = CompleteOrderBody(
                settlementAccount=wallet.broker_account_id,
                forwardReference=ticket.ticket_id
            )
            try:
                data = corpay_api.complete_order(
                    forward_id=ticket.broker_id, data=complete_order_data)
            except Exception as e:
                logger.exception(e)

            try:
                ticket.trade_details['completion'] = data
            except:
                pass

        if data:
            return True
        else:
            return False

    # ===============

    method_map = {
        'Wire': 'W',
        'EFT': 'E',
        'StoredValue': 'C',
    }

    mp_method_map = {
        'W': 'Wire',
        'E': 'EFT',
        'C': 'StoredValue'
    }

    # ===============

    def _map_pangea_purpose_to_corpay(self, purpose: int):
        match int(purpose):
            case Beneficiary.Purpose.INTERCOMPANY_PAYMENT:
                return Beneficiary.CorpayPurpose.INTERCOMPANY_PAYMENT.value[0]
            case Beneficiary.Purpose.PURCHASE_SALE_OF_GOODS:
                return Beneficiary.CorpayPurpose.PURCHASE_OF_GOODS.value[0]
            case Beneficiary.Purpose.PURCHASE_SALE_OF_SERVICES:
                return Beneficiary.CorpayPurpose.PURCHASE_PROFESSIONAL_SERVICE.value[0]
            case Beneficiary.Purpose.PERSONNEL_PAYMENT:
                return Beneficiary.CorpayPurpose.PAYROLL_PERSONNEL_PAYMENT.value[0]
            case Beneficiary.Purpose.FINANCIAL_TRANSACTION:
                return Beneficiary.CorpayPurpose.PAYMENT_FOR_A_LOAN_OR_DEPOSIT.value[0]
            case Beneficiary.Purpose.OTHER:
                # Since corpay does not seem to have OTHER, internal purpose OTHER
                # was updated to map to PROFESSIONAL_FEES_PAYMENT and
                # PURCHASE_SALE_OF_SERVICES to PURCHASE_PROFESSIONAL_SERVICE
                return Beneficiary.CorpayPurpose.PROFESSIONAL_FEES_PAYMENT.value[0]

    def settle(self, ticket, *args, **kwargs):
        beneficiary_service = CorpayBeneficiaryService(
            company=ticket.as_django_model().company)
        beneficiary_field_mappings = beneficiary_service.get_broker_value_mapping(
            beneficiary_to_broker=True)
        data = None
        company = ticket.get_company()

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:

            if ticket.beneficiaries and len(ticket.beneficiaries) > 1:
                # NOTE: no need to settle a mass payment
                return True

            available = ticket.internal_quote_info['payment']['amount']

            orders = []
            orders.append(
                InstructDealOrder(
                    orderId=ticket.broker_id,
                    amount=available,
                )
            )

            payments = []

            close = (len(ticket.beneficiaries) == 1)

            buy_currency = ticket.get_buy_currency()
            sell_currency = ticket.get_sell_currency()

            beneficiary_ids = [b['beneficiary_id']
                               for b in ticket.beneficiaries]

            # Fetch all relevant wallets and beneficiaries in bulk
            wallets = {str(w.wallet_id): w for w in
                       Wallet.objects.filter(wallet_id__in=beneficiary_ids, broker=self.broker_model)}
            beneficiary_brokers = {
                str(bb.beneficiary.beneficiary_id): bb
                for bb in BeneficiaryBroker.objects.filter(beneficiary__beneficiary_id__in=beneficiary_ids,
                                                           broker=self.broker_model)
                .select_related('beneficiary', 'broker')
            }

            for beneficiary in ticket.beneficiaries:
                beneficiary_id = beneficiary['beneficiary_id']
                wallet = wallets.get(beneficiary_id)
                beneficiary_broker = beneficiary_brokers.get(beneficiary_id)

                if close:
                    amount = available
                else:
                    raise NotImplementedError
                    amount = beneficiary.get('amount', ticket.amount)
                    if amount > available:
                        logger.warn(
                            f'ERROR: trying to drawdown more than available balance {available}')

                available -= amount

                if wallet:
                    method = 'C'
                    beneficiary_id = wallet.broker_account_id
                if beneficiary_broker:
                    mappings = beneficiary_field_mappings['preferred_method']
                    method = mappings[beneficiary_broker.beneficiary.preferred_method]
                    beneficiary_id = beneficiary_broker.broker_beneficiary_id

                payments.append(
                    InstructDealPayment(
                        amount=amount,
                        beneficiaryId=beneficiary_id,
                        deliveryMethod=method,
                        currency=buy_currency.mnemonic,
                        purposeOfPayment=self._map_pangea_purpose_to_corpay(
                            beneficiary['purpose_of_payment']),
                        paymentReference=beneficiary.get('reference')
                    )
                )

            if available < 0.0:
                logger.warn(
                    f'ERROR: trying to drawdown more than available balance {available}')
            elif available > 0.0:
                # TODO: add drawdown into wallet
                logger.warn(f'ERROR: leftover funds {available}')

            settlements = []
            first_settlement_account = None
            first_settlement_account_method = None
            for settlement_info in ticket.settlement_info:
                wallet = Wallet.objects.get(
                    wallet_id=settlement_info['settlement_account_id'])

                method = None
                if wallet.type == Wallet.WalletType.SETTLEMENT:
                    if wallet.method == Wallet.WalletMethod.WIRE:
                        method = 'W'
                    if wallet.method == Wallet.WalletMethod.EFT:
                        method = 'E'
                if wallet.type == Wallet.WalletType.WALLET:
                    method = 'C'
                if not first_settlement_account:
                    first_settlement_account = wallet
                    first_settlement_account_method = method
                if not method:
                    raise ValueError(
                        f'Invalid settlement method, ticket id: {str(ticket.ticket_id)} | wallet_id: {str(wallet.wallet_id)}')

                settlements.append(
                    InstructDealSettlement(
                        accountId=wallet.broker_account_id,
                        deliveryMethod=method,
                        currency=sell_currency.mnemonic,
                        purpose='Spot'
                    )
                )

            # bill customer for wire fees?
            if True and first_settlement_account is not None and first_settlement_account_method is not None:
                settlements.append(
                    InstructDealSettlement(
                        accountId=first_settlement_account.broker_account_id,
                        deliveryMethod=first_settlement_account_method,
                        currency=sell_currency.mnemonic,
                        purpose='Fee'
                    )
                )

            instruct_deal_body = InstructDealBody(
                orders=orders,
                payments=payments,
                settlements=settlements
            )

            company = ticket.get_company()
            corpay_api = CorPayExecutionServiceFactory.for_company(company)

            try:
                data = corpay_api.instruct_spot_deal(instruct_deal_body)
            except Exception as e:
                logger.exception(e)

            if data:
                ticket.trade_details['instructions'] = data
                ticket.save()
                return True
            else:
                return False

        elif ticket.instrument_type == Ticket.InstrumentTypes.FWD:
            return self.drawdown(ticket)

        if data:
            return True
        else:
            return False

    def drawdown(self, ticket, *args, close=False, fees=False, **kwargs):

        data = None

        if ticket.instrument_type == Ticket.InstrumentTypes.FWD:

            if ticket.rfq_type != CnyExecution.RfqTypes.API or not ticket.broker_id:
                return True

            company = ticket.get_company()
            corpay_api = CorPayExecutionServiceFactory.for_company(company)

            _forward = corpay_api.get_forward_details(ticket.broker_id)
            open_date = parse_datetime(_forward['openFrom'])

            if _forward is None:  # TODO: or date.now() < open_date:
                return False

            drawdown_order = DrawdownOrder(
                orderId=_forward['ordNum'],
                amount=_forward['amount']
            )

            # this is where you set the fee
            drawdown_fee = DrawdownPaymentFee(
                expectataion='AnyFee',
                amount=0,
                currency=_forward['costCurrency']
            )

            """
            drawdown_fee = DrawdownPaymentFee(
                expectataion='ExactFee',
                amount=fees['fee_amount_usd'],
                currency='USD'
            )
            """

            drawdown_payments = []
            available = _forward['availableBalance']

            close = (len(ticket.beneficiaries) == 1)
            lock_side = ticket.get_lock_side()

            beneficiary_service = CorpayBeneficiaryService(
                company=ticket.as_django_model().company)
            beneficiary_field_mappings = beneficiary_service.get_broker_value_mapping(
                beneficiary_to_broker=True)
            beneficiary_ids = [b['beneficiary_id']
                               for b in ticket.beneficiaries]

            # Fetch all relevant wallets and beneficiaries in bulk
            wallets = {str(w.wallet_id): w for w in
                       Wallet.objects.filter(wallet_id__in=beneficiary_ids, broker=self.broker_model)}
            beneficiary_brokers = {
                str(bb.beneficiary.beneficiary_id): bb
                for bb in BeneficiaryBroker.objects.filter(beneficiary__beneficiary_id__in=beneficiary_ids,
                                                           broker=self.broker_model)
                .select_related('beneficiary', 'broker')
            }

            for beneficiary in ticket.beneficiaries:
                beneficiary_id = beneficiary['beneficiary_id']
                wallet = wallets.get(beneficiary_id)
                beneficiary_broker = beneficiary_brokers.get(beneficiary_id)

                if close:
                    amount = available
                else:
                    if lock_side.mnemonic == _forward['currency']:
                        amount = beneficiary.get('amount', ticket.amount)
                        if amount > available:
                            logger.warn(
                                f'ERROR: trying to drawdown more than available balance {available}')
                    else:
                        amount_pct = beneficiary.get('amount_pct')
                        if amount_pct is None:
                            raise ValueError
                        # round down amount
                        amount = int(available * amount_pct)

                available -= amount

                if wallet:
                    method = 'C'
                    beneficiary_id = wallet.broker_account_id
                elif beneficiary_broker:
                    mappings = beneficiary_field_mappings['preferred_method']
                    method = mappings[beneficiary_broker.beneficiary.preferred_method]
                    beneficiary_id = beneficiary_broker.broker_beneficiary_id
                else:
                    raise ValueError(
                        f"No wallet or beneficiary broker found for beneficiary ID: {beneficiary_id}")

                drawdown_payments.append(
                    DrawdownPayment(
                        beneficiaryId=beneficiary_id,
                        deliveryMethod=method,
                        amount=amount,
                        currency=_forward['currency'],
                        purposeOfPayment=beneficiary['purpose_of_payment'],
                        fee=drawdown_fee
                    )
                )

            if available < 0.0:
                logger.warn(
                    f'ERROR: trying to drawdown more than available balance {available}')
            elif available > 0.0:
                # TODO: add drawdown into wallet
                logger.warn(f'ERROR: leftover funds {available}')

            drawdown_settlements = []
            first_settlement_account = None
            first_settlement_account_method = None
            dj_ticket = ticket.as_django_model()

            for settlement_info in dj_ticket.settlement_info:
                wallet = Wallet.objects.get(
                    wallet_id=settlement_info['settlement_account_id'])

                method = None
                if wallet.type == Wallet.WalletType.SETTLEMENT:
                    if wallet.method == Wallet.WalletMethod.WIRE:
                        method = 'W'
                    if wallet.method == Wallet.WalletMethod.EFT:
                        method = 'E'
                if wallet.type == Wallet.WalletType.WALLET:
                    method = 'C'

                if not first_settlement_account:
                    first_settlement_account = wallet
                    first_settlement_account_method = method

                if not method:
                    raise ValueError(
                        f'Invalid settlement method, ticket id: {str(ticket.ticket._id)}')

                drawdown_settlements.append(
                    DrawdownSettlement(
                        accountId=wallet.broker_account_id,
                        deliveryMethod=method,
                        currency=_forward['costCurrency'],
                        purpose='Drawdown'
                    )
                )

            # Add fee settlement if applicable
            if fees and first_settlement_account is not None and first_settlement_account_method is not None:
                drawdown_settlements.append(
                    DrawdownSettlement(
                        accountId=first_settlement_account.broker_account_id,
                        deliveryMethod=first_settlement_account_method,
                        currency=_forward['costCurrency'],
                        purpose='Fee'
                    )
                )

            drawdown_body = DrawdownBody(
                orders=[
                    drawdown_order
                ],
                payments=drawdown_payments,
                settlements=drawdown_settlements
            )
            response = corpay_api.book_drawdown(data=drawdown_body)
            if not response:
                return False

            try:
                ticket.trade_details['drawdownId'] = response['ordNum']
            except:
                ...

            ticket.save()

        elif ticket.instrument_type == Ticket.InstrumentTypes.WINDOW_FWD:
            raise NotImplementedError
            # TODO: call a drawdown
            ticket = ticket.as_django_model()
            company = ticket.company
            broker = Broker.objects.get(name='Corpay')
            corpay_api = CorPayExecutionServiceFactory.for_company(company)
            drawdown_data = get_corpay_drawdown_data(
                ticket, broker, corpay_api)
            try:
                data = corpay_api.book_drawdown(data=drawdown_data)
            except Exception as e:
                logger.exception(e)
                data = None

        if data:
            return True
        else:
            return False

    def inspect(self, ticket, *args, **kwargs):

        data = None

        if ticket.broker_id:

            company = ticket.get_company()
            corpay_api = CorPayExecutionServiceFactory.for_company(company)

            if ticket.instrument_type == Ticket.InstrumentTypes.WINDOW_FWD:
                # order_number = ticket.trade_details['ordNum']
                data = corpay_api.get_forward_details(ticket.broker_id)
            elif ticket.instrument_type == Ticket.InstrumentTypes.FWD:
                # order_number = ticket.trade_details['ordNum']
                data = corpay_api.get_forward_details(ticket.broker_id)
            elif ticket.instrument_type == Ticket.InstrumentTypes.SPOT:
                data = corpay_api.get_order_details(ticket.broker_id)

    def time_to_settle(self, ticket, *args, **kwargs):

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:
            return True
        elif ticket.instrument_type == Ticket.InstrumentTypes.NDF:
            now_date = datetime.now().date()
            return ticket.value_date == now_date
        elif ticket.rfq_type != CnyExecution.RfqTypes.API:
            return True

        data = self.inspect(ticket)
        if data:
            status = data.get('statusDesc')
            if status == 'Available':
                return True

    def pre_exec_check(self, ticket, *args, **kwargs):

        if ticket.rfq_type != CnyExecution.RfqTypes.API:
            return True

        if ticket.instrument_type == Ticket.InstrumentTypes.FWD:
            pay_amount = ticket.internal_quote_info['payment']
            settle_amount = ticket.internal_quote_info['settlement']
            cost = settle_amount['amount']
            cost_ccy = settle_amount['currency']
            amount = pay_amount['amount']
            amount_ccy = pay_amount['currency']
        elif ticket.instrument_type == Ticket.InstrumentTypes.SPOT:
            pay_amount = ticket.internal_quote_info['payment']
            settle_amount = ticket.internal_quote_info['settlement']
            cost = settle_amount['amount']
            cost_ccy = settle_amount['currency']
            amount = pay_amount['amount']
            amount_ccy = pay_amount['currency']
        else:
            return False

        corpay_sell_currency = Currency.get_currency(currency=cost_ccy)
        corpay_buy_currency = Currency.get_currency(currency=amount_ccy)

        sell_currency = ticket.get_sell_currency()
        buy_currency = ticket.get_buy_currency()
        lock_side = ticket.get_lock_side()

        if corpay_buy_currency != buy_currency:
            ret = False
        elif corpay_sell_currency != sell_currency:
            ret = False
        elif lock_side == buy_currency and ticket.amount != amount:
            ret = False
        elif lock_side == sell_currency and ticket.amount != cost:
            ret = False
        else:
            ret = True

        if not ret:
            ticket.error_message = 'failed pre-exec check'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            ticket.save()
            return False

        return True


# =========

corpay_interface = CorpayInterface()

RfqInterface.register(corpay_interface)
RfqInterface.register(corpay_interface, key='CORPAY_MP')


# ============================================

class CorpayMpInterface(RfqInterface):

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.broker = 'CORPAY_MP'
        self._broker_model = None

    @property
    def broker_model(self) -> str:
        if not self._broker_model:
            self._broker_model = Broker.objects.get(name='Corpay')
        return self._broker_model

    def get_fees(self, buy_currency: str, sell_currency: str):
        return calculate_corpay_fee(buy_currency, sell_currency, self.broker_model)

    def mp_summarize(self, ticket, paymentSummary, fees):

        payments = defaultdict(float)

        done = cntr_done = rate = extra = None

        lock_ccy = ticket.lock_side.mnemonic

        if lock_ccy == ticket.market_name[:3]:
            done = ticket.amount
        elif lock_ccy == ticket.market_name[3:]:
            cntr_done = ticket.amount

        fee_stripped = False

        for row in paymentSummary:

            # print( row )

            if row['count'] > 1 and not fee_stripped:
                # this means that the fee is included
                pay_ccy = row['paymentCurrency']
                pay_amount = (fees['payment_amount'] *
                              row['rate'])  # amount of dollars
                if pay_ccy != lock_ccy:
                    payments[pay_ccy] += pay_amount
                fee_stripped = True
            else:
                pay_ccy = row['paymentCurrency']
                pay_amount = row['amountTotal']
                if pay_ccy != lock_ccy:
                    payments[pay_ccy] += pay_amount

                if pay_ccy != row['settlementCurrency']:
                    settle_ccy = row['settlementCurrency']
                    settle_amount = row['settlementAmount']
                    if settle_ccy != lock_ccy:
                        payments[settle_ccy] += settle_amount

        for ccy, amount in payments.items():
            if ccy == ticket.market_name[:3]:
                done = amount
            elif ccy == ticket.market_name[3:]:
                cntr_done = amount
            else:
                extra = amount

        if done is not None and cntr_done is not None:
            rate = cntr_done / done
        else:
            rate = 1.0

        return done, cntr_done, rate, extra

    def rfq(self, ticket, *args, internal_only=False, **kwargs):

        # TODO: get recent corpay rate
        dj_ticket = ticket.as_django_model()

        company = dj_ticket.get_company()
        corpay_api = CorPayExecutionServiceFactory.for_company(company)
        fees = self.get_fees(dj_ticket.buy_currency.mnemonic,
                             dj_ticket.sell_currency.mnemonic)

        if not ticket.beneficiaries:
            ticket.error_message = 'ERROR: beneficiary must be populated.'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return False

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:
            lock_side = dj_ticket.get_corpay_lock_side()

            spot_response = get_mp_spot_rate(dj_ticket, company, corpay_api)
            mp_fee = calculate_mp_fee(
                spot_response=spot_response,
                buy_currency=dj_ticket.buy_currency.mnemonic,
                sell_currency=dj_ticket.sell_currency.mnemonic,
                lock_side=dj_ticket.lock_side.mnemonic,
                amount=ticket.amount,
                broker=self.broker_model,
            )
            mp_data = get_mp_data(dj_ticket, mp_fee, company)
            data = corpay_api.quote_payments(data=mp_data)
            data['spotReference'] = spot_response
            data['fees'] = mp_fee
        elif ticket.instrument_type == Ticket.InstrumentTypes.FWD:
            ticket.error_message = 'RFQ FAILED: no corpay mass payments for forwards.'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return False
        else:
            data = None

        if data:

            # oer reference rate
            # ref_rate = get_recent_spot_rate(ticket.market_name)
            # rr = ref_rate['bid'] if ticket.side == 'Sell' else ref_rate['ask']

            # payment summary could be complicated
            # TODO: this needs to be searched. not always in position 0

            for row in data['paymentSummary']:
                buy_ccy = row['paymentCurrency']
                sell_ccy = row['settlementCurrency']
                if buy_ccy == dj_ticket.buy_currency.mnemonic and sell_ccy == dj_ticket.sell_currency.mnemonic:
                    rate = row['rate']
                    break
            else:
                raise

            done, cntr_done, all_in_rate, extra = self.mp_summarize(
                dj_ticket, data['paymentSummary'], data['fees'])

            # logger.debug( 'Id:', dj_ticket.id, 'Buy:', dj_ticket.buy_currency, 'Sell:', dj_ticket.sell_currency, 'LockSide:', dj_ticket.lock_side,
            #         'Amount:', dj_ticket.amount, 'All-in-Done:', done, 'All-in-Cntr-Done:', cntr_done, 'All-in-Rate:', all_in_rate,)

            all_in_fee = fees.broker_fee + fees.pangea_fee

            ticket.quote_fee = fees.broker_fee
            # in bps # this should really be all_in_rate/rate
            ticket.fee = mp_fee['fee']

            ticket.quote_source = self.broker
            ticket.internal_quote_id = '|'.join(
                [data['quote_id'], data['session_id']])
            ticket.internal_quote = rate

            # TODO: pull the expiry time from the response
            ticket.internal_quote_expiry = add_time(
                now(), seconds=19.5)  # this has expiry?
            ticket.internal_quote_info = data

            # spot_rate = get_recent_spot_rate(ticket.market_name)
            # ticket.spot_rate = round(spot_rate['mid'], 5)
            if ticket.side == 'Sell':
                ticket.spot_rate = round(all_in_rate * (1.0 + all_in_fee), 5)
            else:
                ticket.spot_rate = round(all_in_rate * (1.0 - all_in_fee), 5)

            ticket.fwd_points = 0.0

            # exec booking prematurely
            ticket.rate = rate
            ticket.done = done
            ticket.cntr_done = cntr_done
            ticket.all_in_done = ticket.done
            ticket.all_in_cntr_done = ticket.cntr_done
            ticket.all_in_rate = all_in_rate

            if not internal_only:
                # calculate the modified quote
                self.calculate_external_quote(all_in_rate, ticket)

            ticket.change_internal_state(INTERNAL_STATES.RFQ_DONE)
            if ticket.action == Ticket.Actions.RFQ:
                ticket.change_external_state(EXTERNAL_STATES.DONE)

            return True

        else:
            ticket.error_message = 'RFQ FAILED'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return False

    def execute(self, ticket, *args, **kwargs):

        dj_ticket = ticket.as_django_model()
        company = dj_ticket.get_company()
        corpay_api = CorPayExecutionServiceFactory.for_company(company)

        if ticket.instrument_type == Ticket.Tenors.SPOT:
            quote_params = ticket.internal_quote_id.split('|')
            params = BookPaymentsParams(
                quoteKey=quote_params[0],
                loginSessionId=quote_params[1]
            )
            bp_data = BookPaymentsBody(
                combineSettlements=True
            )
            data = corpay_api.book_payments(
                params=params,
                data=bp_data
            )
        elif ticket.instrument_type == Ticket.Tenors.FWD:
            ticket.error_message = 'EXECUTE FAILED: no corpay mass payments for forwards.'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return False
        else:
            data = None

        if data:

            ticket.trade_details = data

            # NOTE: although forwards also return orderNumber, ignore docs bc forwardId is needed
            ticket.broker_id = data['orderNumber']
            ticket.change_internal_state(INTERNAL_STATES.FILLED)

            return False
        else:
            ticket.error_message = 'EXECUTE FAILED'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return True

    def complete(self, ticket, *args, **kwargs):
        return True  # nop for spot, complete for forwards

    def settle(self, ticket, *args, **kwargs):
        return True  # nop for spot, complete for forwards

    def pre_exec_check(self, ticket, *args, **kwargs):
        # check the amounts to ensure proper execution
        return True


# RfqInterface.register(CorpayMpInterface())


# ============================================


class VertoInterface(RfqInterface):

    def __init__(self, *args, **kwargs):
        super().__init__()
        from main.apps.oems.services.brokers.verto import VertoApi
        self.broker = 'VERTO'
        self.api = VertoApi()

    def rfq(self, ticket, *args, internal_only=False, **kwargs):

        # lookup somewhere for market + customer if its api market or manual
        # TODO: THIS IS FAKE. IN REAL LIFE CALL THE PRICING ENGINE

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:

            from_ccy = Currency.objects.get(
                pk=ticket.sell_currency_id).mnemonic
            to_ccy = Currency.objects.get(pk=ticket.buy_currency_id).mnemonic
            data = self.api.get_fx_rate(from_ccy, to_ccy)

        else:
            data = None

        if data:
            ticket.quote_source = self.broker
            ticket.internal_quote_id = data['vfx_token']
            ticket.internal_quote = data['rate']  # which way for testing
            ticket.internal_quote_info = data
            ticket.internal_quote_expiry = parse_datetime(data['expiry'])

            if not internal_only:
                # calculate the modified quote
                self.calculate_external_quote(ticket.internal_quote, ticket)

            ticket.change_internal_state(INTERNAL_STATES.RFQ_DONE)
            if ticket.action == Ticket.Actions.RFQ:
                ticket.change_external_state(EXTERNAL_STATES.DONE)
            return True

        else:
            ticket.error_message = 'RFQ FAILED'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return False

    def execute(self, ticket, *args, **kwargs):

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:
            verto_side = self.api.get_side(ticket)
            data = self.api.create_fx_trade(self, self.ticket.internal_quote_id, ticket.amount, verto_side,
                                            ticket.ticket_id)
        else:
            data = None

        if data:
            ticket.trade_details = data
            ticket.done = data['amountFrom']  # or data['amountTo]
            """
            {
                "id": 140,
                "reference": "EN-16062022-003",
                "amountFrom": "106.00",
                "amountTo": "67.75",
                "rate": "0.6391593000",
                "transactionState": "inward_remittance_pending",
                "clientReference": "Test-1000",
                "currencyFrom": "USD",
                "currencyTo": "GBP"
            }
            """
            ticket.broker_id = data['reference']
            ticket.change_broker_state(data['transactionState'])

            ticket.all_in_rate = ticket.external_quote
            # complete the order data['order_number'], data['forward_id']
            ticket.change_internal_state(INTERNAL_STATES.FILLED)
            return False
        else:
            # TODO: could go to working and try again
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return True

    def complete(self, ticket, *args, **kwargs):
        pass  # nop for spot, complete for forwards

    def settle(self, ticket, *args, **kwargs):
        pass  # TODO

    def pre_exec_check(self, ticket, *args, **kwargs):
        # check that funding is okay
        return False


RfqInterface.register(VertoInterface())


# ============================================

class NiumInterface(RfqInterface):

    def __init__(self, *args, **kwargs):
        super().__init__()
        from main.apps.oems.services.brokers.nium import NiumApi
        from main.apps.nium.services.api.connectors.payout.payout import NiumPayoutConnector

        self.broker = 'NIUM'
        self.api = NiumApi()
        self.payout_api = NiumPayoutConnector()

    @staticmethod
    def parse_datetime(date_string):
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")

    def rfq(self, ticket, *args, internal_only=False, **kwargs):

        # lookup somewhere for market + customer if its api market or manual
        # TODO: THIS IS FAKE. IN REAL LIFE CALL THE PRICING ENGINE

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:

            lock_side = ticket.get_lock_side()
            buy_currency = ticket.get_buy_currency()
            sell_currency = ticket.get_sell_currency()

            customer_hash_id = self.api.get_customer_hash_id(ticket)
            wallet_hash_id = self.api.get_wallet_hash_id(ticket)
            conversion_schedule = self.api.get_conversion_schedule(ticket)
            lock_period = self.api.get_lock_period(ticket)
            exec_type = self.api.get_execution_type(ticket)

            data = self.api.request_for_quote(sell_currency.mnemonic, buy_currency.mnemonic, customer_hash_id,
                                              amount=ticket.amount,
                                              lock_side=lock_side.mnemonic, execution_type=exec_type,
                                              conversion_schedule=conversion_schedule, lock_period=lock_period)

        else:
            data = None

        if data:

            """
            {
              "id": "quote_6wBIHIRhPElAHfcgVaDFZs",
              "netExchangeRate": 0.9075027,
              "expiryTime": "2023-06-16T05:07:03Z",
              "sourceCurrencyCode": "EUR",
              "destinationCurrencyCode": "SGD",
              "quoteType": "balance_transfer",
              "conversionSchedule": "immediate",
              "lockPeriod": "5_mins",
              "executionType": "at_conversion_time",
              "exchangeRate": 0.9139,
              "markupRate": 0.0063973,
              "clientMarkupRate": 0.0053973,
              "ecbExchangeRate": 0.9139,
              "rateCaptureTime": "2023-06-16T01:02:03Z",
              "customerHashId": "abc12345-5d6e-0a8b-c8d7-3a7706a0c312",
              "sourceAmount": 100,
              "destinationAmount": 90.75,
              "destinationMarkupAmount": 0.64,
              "createdTime": "2023-06-16T05:02:03Z"
            }
            """

            # netExchangeRate + markupRate = exchangeRate
            # netExchangeRate + clientMarkupRate = our_rate

            data['wallet_hash_id'] = wallet_hash_id

            ticket.quote_source = self.broker
            ticket.internal_quote_id = data['id']
            ticket.internal_quote = data['netExchangeRate'] + \
                data['clientMarkupRate']
            ticket.internal_quote_info = data
            ticket.internal_quote_expiry = self.parse_datetime(
                data['expiryTime'])
            ticket.external_quote_id = str(uuid.uuid4())
            ticket.external_quote = data['netExchangeRate']
            ticket.external_quote_expiry = ticket.internal_quote_expiry

            ticket.change_internal_state(INTERNAL_STATES.RFQ_DONE)
            if ticket.action == Ticket.Actions.RFQ:
                ticket.change_external_state(EXTERNAL_STATES.DONE)

            ticket.spot_rate = data['exchangeRate']
            ticket.fwd_points = 0.0

            # TODO: do we need to invert rates here

            if ticket.side == 'Sell':
                ticket.quote_fee = round(
                    ((ticket.external_quote / ticket.spot_rate) - 1.0), 5)
            else:
                ticket.quote_fee = round(-((ticket.spot_rate /
                                         ticket.external_quote) - 1.0), 5)

            ticket.fee = 0.0

            if data['sourceCurrencyCode'] == ticket.market_name[:3]:
                ticket.done = data['sourceAmount']  # source amount
                ticket.cntr_done = data['destinationAmount']  # dest amount
            else:
                ticket.done = data['destinationAmount']
                ticket.cntr_done = data['sourceAmount']

            ticket.rate = ticket.internal_quote
            ticket.all_in_rate = ticket.external_quote
            ticket.all_in_done = ticket.done
            ticket.all_in_cntr_done = ticket.cntr_done

            return True

        else:
            ticket.error_message = 'RFQ FAILED'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return False

    def execute(self, ticket, *args, **kwargs):

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:

            customer_hash_id = ticket.internal_quote_info['customerHashId']
            wallet_hash_id = ticket.internal_quote_info['wallet_hash_id']
            comment = self.api.get_comment(ticket)

            source_amount = dest_amount = None

            lock_side = ticket.get_lock_side()
            buy_currency = ticket.get_buy_currency()
            sell_currency = ticket.get_sell_currency()

            if lock_side.mnemonic == sell_currency.mnemonic:
                source_amount = ticket.internal_quote_info['sourceAmount']
            elif lock_side.mnemonic == buy_currency.mnemonic:
                dest_amount = ticket.internal_quote_info['destinationAmount']
            else:
                raise ValueError  # can't happen

            data = self.api.execute_quote(ticket.internal_quote_id, customer_hash_id, wallet_hash_id,
                                          source_amount=source_amount, dest_amount=dest_amount, comment=comment)

        else:
            data = None

        if data:
            ticket.trade_details = data

            """
            {
              "id": "conversion_4UTXo2tQnThdZGrMz6FdQR",
              "status": "processing",
              "conversionTime": "2023-06-16T05:22:14Z",
              "sourceCurrencyCode": "USD",
              "destinationCurrencyCode": "SGD",
              "executionType": "at_conversion_time",
              "sourceAmount": 100,
              "destinationAmount": 132.52,
              "quoteId": "quote_6WRfj2CkYaRSuiPskK3kj3",
              "netExchangeRate": 1.3251652,
              "exchangeRate": 1.3372,
              "markupRate": 0.0120348,
              "clientMarkupRate": 0.0110348,
              "destinationMarkupAmount": 1.2,
              "systemReferenceNumber": "WFT9188961163",
              "customerComments": "Converting USD to SGD",
              "createdTime": "2023-06-16T05:22:14Z",
              "updatedTime": "2023-06-16T05:22:14Z"
            }
            """

            ticket.broker_id = data['id']
            ticket.change_internal_state(INTERNAL_STATES.FILLED)
            return False
        else:
            # TODO: could go to working and try again
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return True

    def settle(self, ticket, *args, **kwargs):

        if ticket.trade_details['executionType'] != 'manual':
            # NO NEED TO EXECUTE unless manual
            return True

        customer_hash_id = ticket.internal_quote_info['customerHashId']
        wallet_hash_id = self.api.get_wallet_hash_id(ticket)
        data = self.api.complete_execution(
            ticket.broker_id, customer_hash_id, wallet_hash_id)

        if data:
            try:
                ticket.trade_details['completion'] = data
            except:
                pass

            # TODO: do payout to beneficiaries here...
            tf_money_resp = self._do_payout(
                ticket=ticket, wallet_hash_id=wallet_hash_id, complete_exec_data=data)

            return True
        else:
            return False

    def complete(self, ticket, *args, **kwargs):
        return True

    def time_to_settle(self, ticket, *args, **kwargs):
        if ticket.trade_details['executionType'] == 'manual':
            # TODO: check that we are not after conversion time else big YIKES!
            wallet_hash_id = ticket.internal_quote_info['wallet_hash_id']
            wallet = Wallet.objects.filter(
                broker_account_id=wallet_hash_id).first()
            try:
                balance = wallet.get_latest_balance(wallet=wallet)
            except Exception as e:
                logger.exception(e)
                raise ValueError('error getting wallet balance')
            # if wallet does not have sufficient balance reject the transaction
            if ticket.settlement_amount and ticket.settlement_amount < balance.available_balance:
                return False
            else:
                return True

        else:
            return True

    def pre_exec_check(self, ticket, *args, **kwargs):

        cost = ticket.internal_quote_info.get('sourceAmount')
        cost_ccy = ticket.internal_quote_info.get('sourceCurrencyCode')
        amount = ticket.internal_quote_info.get('destinationAmount')
        amount_ccy = ticket.internal_quote_info.get('destinationCurrencyCode')

        nium_sell_currency = Currency.get_currency(currency=cost_ccy)
        nium_buy_currency = Currency.get_currency(currency=amount_ccy)

        sell_currency = ticket.get_sell_currency()
        buy_currency = ticket.get_buy_currency()
        lock_side = ticket.get_lock_side()

        ret = True
        if nium_buy_currency != buy_currency:
            ret = False
        elif nium_sell_currency != sell_currency:
            ret = False
        elif lock_side == buy_currency and ticket.amount != amount:
            ret = False
        elif lock_side == sell_currency and ticket.amount != cost:
            ret = False

        wallet_hash_id = ticket.internal_quote_info['wallet_hash_id']
        wallet = Wallet.objects.filter(
            broker_account_id=wallet_hash_id).first()

        try:
            balance = wallet.get_latest_balance(wallet=wallet)
        except Exception as e:
            logger.exception(e)
            raise ValueError('error getting wallet balance')

        # if wallet does not have sufficient balance reject the transaction
        # TODO: if funded via wire, ignore this check

        if cost > balance.available_balance:
            raise ValueError('insufficient funds to execute transaction')

        return ret

    def _do_payout(self, ticket: Ticket, wallet_hash_id: str, complete_exec_data: dict,
                   *args, **kwargs) -> TransferMoneyResponse:

        # TODO contruct payload for NIUM transfer money using
        # main.apps.nium.services.api.dataclasses.payout.TransferMoneyPayload
        beneficiary = BeneficiaryDetail(id='1234')
        payout = Payout()

        # required field
        payload = TransferMoneyPayload(
            additionalFees=None,
            beneficiary=beneficiary,
            payout=payout,
            purposeCode=PurposeCode.DONATIONS.value,
            sourceOfFunds=SourceOfFunds.PERSONAL_SAVINGS.value
        )
        data = self.payout_api.transfer_money(
            wallet_hash_id=wallet_hash_id, data=payload)
        return TransferMoneyResponse(**data)


# ============================================

RfqInterface.register(NiumInterface())


# ============================================

class MonexInterface(RfqInterface):

    def __init__(self, *args, **kwargs):
        super().__init__()
        from main.apps.monex.services.monex import MonexApi
        self.broker = 'MONEX'
        self.api = MonexApi.init()

    def rfq(self, ticket, *args, internal_only=False, **kwargs):

        # lookup somewhere for market + customer if its api market or manual
        # TODO: THIS IS FAKE. IN REAL LIFE CALL THE PRICING ENGINE

        company = ticket.get_company()
        lock_side = ticket.get_lock_side()
        buy_currency = ticket.get_buy_currency()
        sell_currency = ticket.get_sell_currency()

        if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:

            wid = ticket.internal_quote_id  # refresh
            data = self.api.get_quick_rate(company, sell_currency.mnemonic,
                                           buy_currency.mnemonic, lock_side.mnemonic, ticket.amount,
                                           value_date=ticket.value_date, wid=wid)  # TODO: could do spot=True

            rates = data['quotedData']['rates']

            if len(rates) > 1:
                # we don't support multi-currency payments yet
                logger.error(f'multiple rates found: {rates}')
                raise ValueError

            rate = float(rates[0]['realRate'])
            all_in_rate = float(rates[0]['displayRate'])
            quote_expiry_secs = data['quoteTimerSecs']
            buy_amount = float(rates[0]['amount'])
            sell_amount = float(rates[0]['cost'])

            """
                # {'firstQuote': True,
                'quotedData': {'rates': [{'pairCCY1': 42, 'pairCCY2': 1,
                'isBuy': False, 'displayRate': '1.0897',
                'markupPercentage': '',
                'realRate': 0.9176837661741765,
                'amount': '917.68', 'cost': 1000,
                'amountCCY': 42, 'costCCY': 1, 'exchangeRateIsLowerThanMarketRate': False}],
                'pays': [], 'totals': [], 'err': False}, 'quoteTimerSecs': 30,
                'wid': '79CDA8286B31A52667C9C09C107A15FA', 'tradeDone': False, 'workflow': 'payment'}
            """

        elif ticket.instrument_type == Ticket.InstrumentTypes.FWD:

            wid = ticket.internal_quote_id  # refresh
            data = self.api.get_quick_rate(company, sell_currency.mnemonic,
                                           buy_currency.mnemonic, lock_side.mnemonic, ticket.amount,
                                           value_date=ticket.value_date, wid=wid)

            if "rates" in data['quotedData']:
                rate_data = data['quotedData']['rates'][0]
            else:
                rate_data = data['quotedData']

            rate = all_in_rate = float(
                rate_data['rate']) if 'rate' in rate_data else float(rate_data['displayRate'])
            quote_expiry_secs = data['quoteTimerSecs']
            buy_amount = float(rate_data['amount'])
            sell_amount = float(rate_data['cost'])

            """
            {'data':
                {
                'firstQuote': True,
                'quoteTimerSecs': 30,
                'quotedData':
                    {'valueDate': '2024-07-23T20:00:00-04:00',
                        'symbolCcy1Id': 42, 'symbolCcy2Id': 1, 'rate': '1.0907',
                        'amountCcyId': 42, 'amount': '916.84',
                        'costCcyId': 1, 'cost': 1000, 'margin': 4, 'marginCcyId': 1,
                        'marginAmount': 40,
                        'exchangeRateIsLowerThanMarketRate': False
                    }
                }
            }
            """

        else:

            data = None

        if data:

            ticket.quote_source = self.broker
            ticket.internal_quote_id = data['wid']
            ticket.internal_quote = rate
            ticket.internal_quote_info = data
            ticket.internal_quote_expiry = add_time(
                now(), seconds=quote_expiry_secs)
            ticket.external_quote_id = str(uuid.uuid4())
            ticket.external_quote = all_in_rate
            ticket.external_quote_expiry = ticket.internal_quote_expiry

            ticket.change_internal_state(INTERNAL_STATES.RFQ_DONE)
            if ticket.action == Ticket.Actions.RFQ:
                ticket.change_external_state(EXTERNAL_STATES.DONE)

            if buy_currency.mnemonic == sell_currency.mnemonic:
                rr = 1.0
            else:
                # oer reference rate
                ref_rate = get_recent_spot_rate(ticket.market_name)
                rr = ref_rate['bid'] if ticket.side == 'Sell' else ref_rate['ask']

            if ticket.instrument_type == Ticket.InstrumentTypes.SPOT:

                ticket.spot_rate = rr
                ticket.fwd_points = 0.0

                if ticket.side == 'Sell':
                    ticket.quote_fee = round(
                        ((ticket.external_quote / rr) - 1.0), 5)
                else:
                    ticket.quote_fee = round(-((rr /
                                             ticket.external_quote) - 1.0), 5)

                ticket.fee = 0.0

            elif ticket.instrument_type == Ticket.InstrumentTypes.FWD:

                ticket.spot_rate = rr

                spot_rate = rr
                ticket.fwd_points = round(ticket.internal_quote - spot_rate, 5)
                implied_fwd_rate = rr + ticket.fwd_points

                if ticket.side == 'Sell':
                    ticket.quote_fee = round(
                        ((ticket.external_quote / implied_fwd_rate) - 1.0), 5)
                else:
                    ticket.quote_fee = round(-((implied_fwd_rate /
                                             ticket.external_quote) - 1.0), 5)

                ticket.fee = 0.0

            # TODO: finish done/cntr_done amounts
            if ticket.side == 'Sell':
                ticket.done = sell_amount
                ticket.cntr_done = buy_amount
            else:
                ticket.done = buy_amount
                ticket.cntr_done = sell_amount

            ticket.rate = ticket.internal_quote
            ticket.all_in_rate = ticket.external_quote
            ticket.all_in_done = ticket.done
            ticket.all_in_cntr_done = ticket.cntr_done

            return True

        else:
            ticket.error_message = 'RFQ FAILED'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return False

    def execute(self, ticket: Ticket, *args, **kwargs):
        data = self.api.execute_payment_rate(ticket.get_company(), ticket.internal_quote_id,
                                             workflow=ticket.internal_quote_info['workflow'])

        if not data:
            ticket.change_internal_state(INTERNAL_STATES.FILLED)
            return False
        else:
            # TODO: could go to working and try again
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return True

    def settle(self, ticket: Ticket, *args, **kwargs):

        workflow = ticket.internal_quote_info['workflow']

        if workflow == 'payment':
            logger.info("Starting Monex payment flow")
            data = self.api.settle_payment(ticket.get_company(), ticket.internal_quote_id, ticket.beneficiaries,
                                           ticket.settlement_info)
            ticket.broker_id = data['dealNumber']
            ticket.trade_details = data
            return True
        elif workflow == 'forward':
            logger.info("Starting Monex forward flow")
            data = self.api.drawdown_forward(*args, **kwargs)

    def complete(self, ticket: Ticket, *args, **kwargs):
        workflow = ticket.internal_quote_info['workflow']

        data = self.api.complete_payment_rate(
            ticket.get_company(), ticket.internal_quote_id, workflow=workflow)

        if workflow == 'forward':
            ticket.broker_id = data['dealNumber']
            ticket.trade_details = data
        else:
            # nop from spot... spot needs to settle to get deal number
            ...

        return True

    def time_to_settle(self, ticket, *args, **kwargs):

        workflow = ticket.internal_quote_info['workflow']

        if workflow == 'payment':
            return True
        elif workflow == 'forward' or ticket.instrument_type == Ticket.InstrumentTypes.NDF \
                or ticket.instrument_type == Ticket.InstrumentTypes.FWD:
            now_date = datetime.now().date()
            return ticket.value_date == now_date

    def pre_exec_check(self, ticket, *args, **kwargs):

        workflow = ticket.internal_quote_info['workflow']

        if workflow == 'forward':
            cost = float(ticket.internal_quote_info['quotedData']['cost'])
            cost_ccy = ticket.internal_quote_info['quotedData']['costCcyId']
            amount = float(ticket.internal_quote_info['quotedData']['amount'])
            amount_ccy = ticket.internal_quote_info['quotedData']['amountCcyId']
        elif workflow == 'payment':
            rates = ticket.internal_quote_info['quotedData']['rates']
            cost = float(rates[0]['cost'])
            cost_ccy = rates[0]['costCCY']
            amount = float(rates[0]['amount'])
            amount_ccy = rates[0]['amountCCY']

        monex_sell_currency = self.api.monex_id_to_currency(cost_ccy)
        monex_buy_currency = self.api.monex_id_to_currency(amount_ccy)

        sell_currency = ticket.get_sell_currency()
        buy_currency = ticket.get_buy_currency()
        lock_side = ticket.get_lock_side()

        if monex_buy_currency != buy_currency:
            ret = False
        elif monex_sell_currency != sell_currency:
            ret = False
        elif lock_side == buy_currency and ticket.amount != amount:
            ret = False
        elif lock_side == sell_currency and ticket.amount != cost:
            ret = False
        else:
            ret = True

        if not ret:
            ticket.error_message = 'failed pre-exec check'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            ticket.save()
            return False

        return True


# ============================================

RfqInterface.register(MonexInterface())


# ============================================

# TODO: convera
# TODO: airwallex
# TODO: ofx

# ========================
# these are the methods that get called by the EMS
# technically no need for one layer of abstraction but its fine for now

def do_indicative_rfq(ticket, *args, **kwargs):
    try:
        return RfqInterface.do_indicative_rfq(ticket, *args, **kwargs)
    except Exception as e:
        ticket.error_message = f'ERROR: rfq - {e}'
        ticket.change_internal_state(INTERNAL_STATES.FAILED)
        ticket.save()
        logger.exception(e)
        return False


def do_api_rfq(ticket, *args, **kwargs):
    try:
        return RfqInterface.do_api_rfq(ticket, *args, **kwargs)
    except Exception as e:
        ticket.error_message = f'ERROR: rfq - {e}'
        ticket.change_internal_state(INTERNAL_STATES.FAILED)
        ticket.save()
        logger.exception(e)
        return False


def do_api_execute(ticket, *args, **kwargs):
    try:
        return RfqInterface.do_api_execute(ticket, *args, **kwargs)
    except Exception as e:
        ticket.error_message = f'ERROR: execute - {e}'
        ticket.change_internal_state(INTERNAL_STATES.FAILED)
        ticket.save()
        logger.exception(e)
        return False


def do_api_complete(ticket, *args, **kwargs):
    try:
        return RfqInterface.do_api_complete(ticket, *args, **kwargs)
    except Exception as e:
        ticket.error_message = f'ERROR: complete - {e}'
        ticket.save()
        logger.exception(e)
        return False


def do_api_tts(ticket, *args, **kwargs):
    try:
        return RfqInterface.do_api_tts(ticket, *args, **kwargs)
    except Exception as e:
        ticket.error_message = f'ERROR: tts - {e}'
        ticket.save()
        logger.exception(e)
        return False


def do_pre_exec_check(ticket, *args, **kwargs):
    try:
        return RfqInterface.do_pre_exec_check(ticket, *args, **kwargs)
    except Exception as e:
        ticket.error_message = f'ERROR: pre-exec-check - {e}'
        ticket.save()
        logger.exception(e)
        return False


def do_api_settle(ticket, *args, **kwargs):
    try:
        return RfqInterface.do_api_settle(ticket, *args, **kwargs)
    except Exception as e:
        ticket.error_message = f'ERROR: settle - {e}'
        ticket.save()
        logger.exception(e)
        return False
