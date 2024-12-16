import logging
import uuid
from datetime import date, datetime, timedelta

import pytz
from django.core.management.base import BaseCommand

from main.apps.account.models import Company
from main.apps.corpay.models import Beneficiary as CorpayBeneficiary, SettlementAccount
from main.apps.corpay.models.fx_forwards import SpotRate, Forward
from main.apps.corpay.services.corpay import CorPayExecutionServiceFactory
from main.apps.currency.models import Currency
from main.apps.oems.backend.ccy_utils import determine_rate_side
from main.apps.oems.backend.date_utils import parse_datetime
from main.apps.oems.backend.states import INTERNAL_STATES, EXTERNAL_STATES, PHASES
from main.apps.oems.models.ticket import Ticket
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.payment import PaymentService


# ========

def parse_currency(x):
    return Currency.get_currency(currency=x)

def parse_company(x):
    return Company.objects.get(pk=int(x))

def check_for_payment( cashflow_id ):
    return Payment.objects.get(cashflow_generator__cashflows__cashflow_id=cashflow_id)

# ========

logger = logging.getLogger(__name__)
logging.disable(logging.DEBUG)


# ===========


def check_single_sa(company, currency):
    corpay_settlement_account = SettlementAccount.objects.filter(company=company, currency=currency)
    if corpay_settlement_account.count() == 1:
        settlement_account = corpay_settlement_account.first()
        return settlement_account.text, settlement_account.delivery_method
    return None, None


def check_single_bene(company, currency):
    corpay_beneficiary = CorpayBeneficiary.objects.filter(company=company, currency=currency)
    if corpay_beneficiary.count() == 1:
        beneficiary = corpay_beneficiary.first()
        method = None
        return beneficiary.client_integration_id, method
    return None, None


def backfill_spot_order( order_number, company, dry_run=False ):

    try:
        ticket = Ticket.objects.get(broker_id=order_number)
        if ticket:
            logger.info(f'Ticket found with order number: {order_number}')
            return
    except:
        ...

    logger.info(f'No spot ticket found with order number: {order_number} for {company.name}... backfill here')

    corpay_api = CorPayExecutionServiceFactory.for_company(company)

    purpose_of_payment = None
    beneficiaries = None
    settlement_info = None
    beneid = reference = method = None
    settle_account_id = settle_method = None

    try:
        order_details = corpay_api.get_order_details(order_number)
    except:
        order_details = None

    if not order_details:
        return

    mp = False

    if len(order_details['payments']) > 1:
        payment = None
        for _ in order_details['payments']:
            if _['reference'] == 'Pangea Spot Transaction Fee':
                mp = True
            else:
                payment = _

    else:
        payment = order_details['payments'][0]

    if len(order_details['settlements']) > 1:
        raise NotImplementedError
    else:
        settlement = order_details['settlements'][0]

    # TODO: this can be one to many
    beneid = payment['beneId']
    reference = payment['reference']
    method = payment['method']
    settle_account_id = settlement['accountId']
    settle_method = settlement['method']

    if not beneid:
        beneid, method = check_single_bene(company, buy_currency)
        if not method:
            method = 'W'

    if not settle_account_id:
        settle_account_id, settle_method = check_single_sa(company, sell_currency)

    if beneid:
        beneficiaries = []
        for _ in order_details['payments']:
            if _['reference'] == 'Pangea Spot Transaction Fee': continue
            beneficiaries.append({"beneficiary_id": _['beneId'], "method": _['method'], "purpose_of_payment": None})

    if settle_account_id:
        settlement_info = [{"settlement_account_id": settle_account_id, "method": settle_method,
         "payment_reference": reference}]

    # ========================================

    # summary = order_details['orderDetail']

    buy_currency = parse_currency( payment['currency'] )
    sell_currency = parse_currency( payment['estimateCostCurrency'] if 'estimateCostCurrency' in payment else payment['costCurrency'] )

    fxpair, side = determine_rate_side(sell_currency, buy_currency)
    market_name = fxpair.market

    if mp:
        lock_side = buy_currency
        cost_amount = settlement['amount'] # sell
        amount = payment['amount'] # buy
        if market_name.startswith('USD'):
            rate = (amount/cost_amount)
        else:
            raise NotImplementedError
    else:
        raise NotImplementedError

    transaction_date = parse_datetime(order_details['orderDetail']['entryDate'])
    value_date = parse_datetime(payment['availableDate']).date()

    logger.info(f'adding spot transaction {market_name} {side} {lock_side.mnemonic} {amount} {cost_amount} {rate}')
    if dry_run: return

    try:
        payment = Payment.objects.get(payment_ident=order_number)
    except:
        payment = None

    name = f'{company.name}: {market_name}'
    payment_status = Payment.PaymentStatus.DELIVERED
    
    if not payment:    
        payment_info = dict(
            company=company,
            name=name,
            amount=amount,
            cntr_amount=cost_amount,
            buy_currency=buy_currency.mnemonic,
            sell_currency=sell_currency.mnemonic,
            lock_side=lock_side.mnemonic,
            delivery_date=value_date,
            payment_status=payment_status,
            execution_timing='immediate',
            payment_ident=order_number,
            purpose_of_payment=purpose_of_payment,
            origin_account_id=settle_account_id,
            origin_account_method=settle_method,
            destination_account_id=beneid,
            destination_account_method=method,
        )

        payment = PaymentService.create_payment(
            **payment_info,
        )

    cashflow = payment.cashflow_generator.cashflows.first()
    cashflow_id = cashflow.id

    # ================

    tid = str(uuid.uuid4())
    instrument_type = tenor = 'spot'

    if (side == 'Sell' and lock_side.mnemonic == buy_currency.mnemonic) or (
        side == 'Buy' and lock_side.mnemonic == sell_currency.mnemonic):
        done = all_in_done = cost_amount
        cntr_done = all_in_cntr_done = amount
    else:
        done = all_in_done = amount
        cntr_done = all_in_cntr_done = cost_amount

    print(market_name, side, lock_side.mnemonic, done, cntr_done)
    all_in_rate = rate

    internal_state = INTERNAL_STATES.DONE
    external_state = EXTERNAL_STATES.DONE
    phase = PHASES.RECON

    ticket_info = dict(
        company=company,
        amount=amount if lock_side.mnemonic == buy_currency.mnemonic else cost_amount,
        sell_currency=sell_currency,
        buy_currency=buy_currency,
        fxpair=fxpair,
        market_name=market_name,
        side=side,
        lock_side=lock_side,
        tenor=tenor,
        value_date=value_date,
        transaction_time=transaction_date,
        cashflow_id=cashflow_id,
        instrument_type=instrument_type,
        time_in_force='gtc',
        ticket_type='payment',
        action='execute',
        execution_strategy='market',
        done=done,
        cntr_done=cntr_done,
        external_quote=all_in_rate,
        rate=rate,
        all_in_done=all_in_done,
        all_in_rate=all_in_rate,
        all_in_cntr_done=all_in_cntr_done,
        broker_id=order_number,
        broker='CORPAY_MP' if mp else 'CORPAY',
        draft=False,
        with_care=False,
        internal_state=internal_state,
        external_state=external_state,
        phase=phase,
        beneficiaries=beneficiaries,
        settlement_info=settlement_info,
    )

    ticket = Ticket(
        ticket_id=tid,
        **ticket_info,
    )
    ticket.save()

    if not cashflow.ticket_id:
        cashflow.ticket_id = ticket.ticket_id
        cashflow.save()

# =====================

def check_manual_fill( ticket, forward ):

    # might need a better check
    if ticket.action == Ticket.Actions.EXECUTE:
        # this will never happen because right now we can't associate a ticket with a deal number
        if ticket.internal_state == INTERNAL_STATES.WORKING and ticket.rfq_type != CnyExecution.RfqTypes.API:

            fwd_id = forward['forwardId'] or forward['ordNum']

            buy_currency = ticket.get_buy_currency()
            sell_currency = ticket.get_sell_currency()
            lock_side = ticket.lock_side()

            amount = forward['amount']
            cost_amount = forward['costAmount']

            if side == 'Sell':
                rate = all_in_rate = 1.0 / forward['rate']
            else:
                rate = all_in_rate = forward['rate']

            if (side == 'Sell' and lock_side.mnemonic == buy_currency.mnemonic) or (
                side == 'Buy' and lock_side.mnemonic == sell_currency.mnemonic):
                done = all_in_done = cost_amount
                cntr_done = all_in_cntr_done = amount
            else:
                done = all_in_done = amount
                cntr_done = all_in_cntr_done = cost_amount

            internal_state = INTERNAL_STATES.DONE
            external_state = EXTERNAL_STATES.DONE
            phase = PHASES.RECON

            # could look for mreq as well
            # if there is an associated manual request, you can fill this in.
            ticket_info = dict(
                done=done,
                cntr_done=cntr_done,
                rate=rate,
                all_in_done=all_in_done,
                all_in_rate=all_in_rate,
                all_in_cntr_done=all_in_cntr_done,
                broker_id=fwd_id,
                internal_state=internal_state,
                external_state=external_state,
                phase=phase,
            )

            resave = False
            for k, v in ticket_info.items():
                if hasattr(ticket, k) and getattr(ticket, k) != v:
                    resave = True
                    print('resaving ticket', k, v)
                    setattr(ticket, k, v)
            if resave: ticket.save()

# ==========

def search_for_matching_ticket( buy_currency, sell_currency, buy_amount, sell_amount, value_date, transaction_date ):

    start_date = transaction_date - timedelta(days=1)
    end_date = transaction_date + timedelta(days=1)

    # Perform the query
    tickets = Ticket.objects.filter(
        buy_currency=buy_currency,
        sell_currency=sell_currency,
        value_date=value_date,
        transaction_time__gt=start_date,
        transaction_time__lt=end_date,
        broker_id__isnull=True,
    )

    candidates = []

    for ticket in tickets:
        if ticket.amount == buy_amount or ticket.amount == sell_amount:
            candidates.append(ticket)

    if not candidates:
        return
    elif len(candidates) == 1:
        return candidates[0]
    else:
        logger.info(f'multiple options for ticket: {candidates}')
        return

# ===============================

def check_payment_done( forward, fwd_id, ticket ):

    try:
        payment = Payment.objects.get(payment_ident=fwd_id)
    except:
        payment = None

    if payment and payment.payment_status == Payment.PaymentStatus.BOOKED:
        value_date = parse_datetime(forward['maturityDate']).date()
        # could also check forward available balance = 0.0?
        if date.today() >= value_date:
            payment.payment_status = Payment.PaymentStatus.DELIVERED
            payment.save()

# ===============================            

def backfill_forward( company, forward_id=None, forward=None, only_ndf=False, dry_run=False ):

    if forward is None:
        assert forward_id
        # get forward here
        raise NotImplementedError

    if 'Incomplete' in forward['statusDesc']:
        # logger.info(f'skipping forward: {forward["forwardId"]}')
        return

    if only_ndf and not forward['isExotic']:
        return

    deal_number = forward['deal']
    order_number = forward['ordNum']
    fwd_id = forward['forwardId'] or forward['ordNum']
    ticket = None

    try:
        ticket = Ticket.objects.get(broker_id=fwd_id)
        if ticket:
            # logger.info(f'Ticket found with order number: {fwd_id}')
            if not dry_run:
                check_manual_fill( ticket, forward )
                check_payment_done( forward, fwd_id, ticket )
            return
    except:
        ...

    if not ticket and not forward['forwardId']:
        logger.info(f'found manual trade: {forward}')

    buy_currency = parse_currency(forward['currency'])
    sell_currency = parse_currency(forward['costCurrency'])

    fxpair, side = determine_rate_side(sell_currency, buy_currency)
    market_name = fxpair.market

    # search for manual tickets

    amount = forward['amount']
    cost_amount = forward['costAmount']

    transaction_date = parse_datetime(forward['dealDate'])
    value_date = parse_datetime(forward['maturityDate']).date()

    if ticket is None:
        ticket = search_for_matching_ticket( buy_currency, sell_currency, amount, cost_amount, value_date, transaction_date )
        if ticket:
            logger.info(f'Matching ticket found with order number: {forward}')
            if not dry_run: check_manual_fill( ticket, forward )
            return

    lock_side_candidates = []

    if str(amount).split('.')[-1] == '0':
        nzeros = str(amount).split('.')[0].count('0')
        lock_side_candidates.append({'ccy': buy_currency, 'zeros': nzeros})

    if str(cost_amount).split('.')[-1] == '0':
        nzeros = str(cost_amount).split('.')[0].count('0')
        lock_side_candidates.append({'ccy': sell_currency, 'zeros': nzeros})

    if not lock_side_candidates:
        logger.error(f'no lockside: {forward}')
        lock_side = buy_currency
    elif len(lock_side_candidates) == 1:
        lock_side = lock_side_candidates[0]['ccy']
    else:
        if lock_side_candidates[0]['zeros'] >=  lock_side_candidates[1]['zeros']:
            lock_side = lock_side_candidates[0]['ccy']
        else:
            lock_side = lock_side_candidates[1]['ccy']
        logger.error(f'no obvious lockside: {forward} - using {lock_side}')

    # try to search for a matching ndf ticket

    if ticket: # could check for associated payment but this doesn't play well with the api
        return

    logger.info(f'No ticket found with forward id: {fwd_id}... backfill here')
    if dry_run: return

    if side == 'Sell':
        rate = all_in_rate = 1.0 / forward['rate']
    else:
        rate = all_in_rate = forward['rate']

    # ================
    # add payment here

    purpose_of_payment = None
    order_details = None
    beneid = reference = method = None
    settle_account_id = settle_method = None
    beneficiaries = None
    settlement_info = None

    if not beneid:
        beneid, method = check_single_bene(company, buy_currency)
        if not method:
            method = 'W'

    if not settle_account_id:
        settle_account_id, settle_method = check_single_sa(company, sell_currency)

    if beneid: beneficiaries = [
        {"beneficiary_id": beneid, "method": method, "purpose_of_payment": purpose_of_payment}]

    if settle_account_id: settlement_info = [
        {"settlement_account_id": settle_account_id, "method": settle_method,
         "payment_reference": reference}]

    print('syncing forward:', fwd_id, deal_number, order_number, transaction_date)

    if value_date > date.today():
        payment_status = Payment.PaymentStatus.BOOKED
    else:
        payment_status = Payment.PaymentStatus.DELIVERED

    try:
        payment = Payment.objects.get(payment_ident=fwd_id)
    except:
        payment = None

    if not payment:
        name = f'{company.name}: {order_number}'

        payment_info = dict(
            company=company,
            name=name,
            amount=amount,
            cntr_amount=cost_amount,
            buy_currency=buy_currency.mnemonic,
            sell_currency=sell_currency.mnemonic,
            lock_side=lock_side.mnemonic,
            delivery_date=value_date,
            payment_status=payment_status,
            execution_timing='immediate',
            payment_ident=fwd_id,
            purpose_of_payment=purpose_of_payment,
            origin_account_id=settle_account_id,
            origin_account_method=settle_method,
            destination_account_id=beneid,
            destination_account_method=method,
        )

        payment = PaymentService.create_payment(
            **payment_info,
        )

    cashflow = payment.cashflow_generator.cashflows.first()
    cashflow_id = cashflow.id

    # ================

    tid = str(uuid.uuid4())
    instrument_type = tenor = 'fwd'
    if forward['isExotic']: instrument_type = 'ndf'

    if (side == 'Sell' and lock_side.mnemonic == buy_currency.mnemonic) or (
        side == 'Buy' and lock_side.mnemonic == sell_currency.mnemonic):
        done = all_in_done = cost_amount
        cntr_done = all_in_cntr_done = amount
    else:
        done = all_in_done = amount
        cntr_done = all_in_cntr_done = cost_amount

    internal_state = INTERNAL_STATES.DONE
    external_state = EXTERNAL_STATES.DONE
    phase = PHASES.RECON

    ticket_info = dict(
        company=company,
        amount=amount,
        sell_currency=sell_currency,
        buy_currency=buy_currency,
        fxpair=fxpair,
        market_name=market_name,
        side=side,
        lock_side=lock_side,
        tenor=tenor,
        value_date=value_date,
        transaction_time=transaction_date,
        cashflow_id=cashflow_id,
        instrument_type=instrument_type,
        time_in_force='gtc',
        ticket_type='payment',
        action='execute',
        execution_strategy='market',
        trader=forward['createdBy'],
        done=done,
        cntr_done=cntr_done,
        external_quote=all_in_rate,
        rate=rate,
        all_in_done=all_in_done,
        all_in_rate=all_in_rate,
        all_in_cntr_done=all_in_cntr_done,
        broker_id=fwd_id,
        broker='CORPAY',
        draft=False,
        with_care=False,
        internal_state=internal_state,
        external_state=external_state,
        phase=phase,
        beneficiaries=beneficiaries,
        settlement_info=settlement_info,
    )

    ticket = Ticket(
        ticket_id=tid,
        **ticket_info,
    )
    ticket.save()

    if not cashflow.ticket_id:
        cashflow.ticket_id = ticket.ticket_id
        cashflow.save()

# ===========================

def backfill_forwards( company, only_ndf=False, dry_run=True ):

    corpay_api = CorPayExecutionServiceFactory.for_company(company)

    try:
        forwards = corpay_api.list_forwards()
    except:
        logger.error(f'problem getting corpay credentials for {company.name} {company.id}')
        return

    for forward in forwards['data']['rows']:
        backfill_forward( company, forward=forward, only_ndf=only_ndf, dry_run=dry_run )

# ============================



