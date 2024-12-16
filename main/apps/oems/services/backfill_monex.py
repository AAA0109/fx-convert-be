import logging
import re
import uuid
from datetime import date, datetime, timedelta

import pytz
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from main.apps.broker.models.broker import Broker
from main.apps.broker.models.constants import BrokerProviderOption
from main.apps.monex.services.api.exceptions import BadRequest, MonexAPIException

from main.apps.account.models import Company
from main.apps.corpay.models import Beneficiary as CorpayBeneficiary, SettlementAccount
from main.apps.corpay.models.fx_forwards import SpotRate, Forward
from main.apps.corpay.services.corpay import CorPayExecutionServiceFactory
from main.apps.currency.models import Currency
from main.apps.oems.backend.ccy_utils import determine_rate_side
from main.apps.oems.backend.date_utils import parse_datetime
from main.apps.oems.backend.states import INTERNAL_STATES, EXTERNAL_STATES, PHASES
from main.apps.oems.models import CnyExecution
from main.apps.oems.models.ticket import Ticket
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.payment import PaymentService

from main.apps.monex.services.monex import MonexApi
from main.apps.settlement.models.beneficiary import Beneficiary, BeneficiaryBroker
from main.apps.settlement.models.wallet import Wallet
from django.db import transaction

# ========


def parse_currency(x):
    return Currency.get_currency(currency=x)


def parse_company(x):
    return Company.objects.get(pk=int(x))


def check_for_payment(cashflow_id):
    return Payment.objects.get(cashflow_generator__cashflows__cashflow_id=cashflow_id)

# ========


logger = logging.getLogger(__name__)

# ===========

# main.apps.broker.models.broker.BrokerCompany.get_companies_by_broker


def check_single_sa(company, currency):
    settlement_accounts = Wallet.objects.filter(
        company=company,
        currency=currency,
        type=Wallet.WalletType.SETTLEMENT,
        broker__broker_provider=BrokerProviderOption.MONEX
    )
    if settlement_accounts.count() == 1:
        settlement_account = settlement_accounts.first()
        return settlement_account.wallet_id, settlement_account.method
    return None, None


def check_single_bene(company, currency):
    beneficiary_brokers = BeneficiaryBroker.objects.filter(
        beneficiary__company=company,
        beneficiary__destination_currency=currency,
        broker__broker_provider=BrokerProviderOption.MONEX
    )
    if beneficiary_brokers.count() == 1:
        beneficiary_broker = beneficiary_brokers.first()
        method = beneficiary_broker.beneficiary.preferred_method
        return beneficiary_broker.beneficiary.beneficiary_id, method
    return None, None


def check_single_wallet(company, currency):
    wallets = Wallet.objects.filter(
        company=company,
        currency__mnemonic=currency,
        type=Wallet.WalletType.WALLET,
        broker__broker_provider=BrokerProviderOption.MONEX
    )
    if wallets.count() == 1:
        wallet = wallets.first()
        return wallet.wallet_id, Beneficiary.PaymentSettlementMethod.WALLET
    return None, None
# ==========================


def infer_lock_side(order, buy_amount, buy_currency, sell_amount, sell_currency):
    buy_is_round = float(buy_amount).is_integer() or float(buy_amount) % 1 == 0.5
    sell_is_round = float(sell_amount).is_integer() or float(sell_amount) % 1 == 0.5

    if buy_is_round and not sell_is_round:
        return buy_currency
    elif sell_is_round and not buy_is_round:
        return sell_currency
    else:
        # If both or neither are round, default to sell currency
        return sell_currency


# =========================


"""
[{'postId': 545108, 'dealNumber': '0411968', 'amount': '10626.00',
'currencyId': 1, 'amountCurrency': 'USD', 'costCurrencyId': 42,
'beneNickname': '', 'isHolding': False, 'iftEntityId': None,
'entryDate': 1719942295, 'valueDate': 1719942295, 'initiated': None,
'funded': None, 'sent': None, 'delivered': None, 'entityName': 'Pangea Parent Entity',
'entityId': 14697, 'entityNumber': '0016283', 'trackingId': 'RCBSSSNHNLZY7Z5M'}]~
"""


def get_monex_currency(ccy_id: int):
    monex_api = MonexApi.init()
    return monex_api.monex_id_to_currency(ccy_id)

# ========


def backfill_spot_order(company, order=None, order_number=None, dry_run=False):
    try:
        if order is None:
            assert order_number
            # get order here
            raise NotImplementedError(
                "Fetching order by number not implemented")
        
        order_number = order['dealNumber']

        with transaction.atomic():
            try:
                ticket = Ticket.objects.get(broker_id=order_number)
                logger.info(f'Ticket found with order number: {order_number}')
            except Ticket.DoesNotExist:
                ticket = None
                logger.info(
                    f'No spot ticket found with order number: {order_number} for {company.name}... creating new ticket')

            try:
                payment = Payment.objects.get(payment_ident=order_number)
                logger.info(f'Payment found with order number: {order_number}')
            except Payment.DoesNotExist:
                payment = None
                logger.info(
                    f'No payment found with order number: {order_number} for {company.name}... creating new payment')

            if dry_run:
                return

            monex_api = MonexApi.init()
            try:
                order_details = monex_api.get_spot_settlement_info(
                    order['trackingId'], company=company)
            except BadRequest as e:
                logger.error(
                    f"Bad request when fetching spot settlement info: {str(e)}")
                return
            except MonexAPIException as e:
                logger.error(
                    f"Monex API error when fetching spot settlement info: {str(e)}")
                return

            if not order_details:
                logger.error('No order details for spot payment')
                return

            order['details'] = order_details

            # Flip the currencies and amounts to match our perspective
            buy_currency = parse_currency(order['amountCurrency'])
            buy_amount = float(order['amount'])

            sell_currency = parse_currency(order_details['costCCY'])
            sell_amount = float(order_details['cost'])

            if sell_currency is None or sell_amount is None:
                logger.error(f"Missing sell currency or amount for order {order_number}. Deleting associated data if exists.")
                if ticket:
                    ticket.delete()
                if payment:
                    payment.delete()
                return
            
            if buy_currency == sell_currency:
                logger.info(f"Same buy and sell currency for order {order_number}. Deleting associated data if exists.")
                if ticket:
                    ticket.delete()
                if payment:
                    payment.delete()
                return

            logger.debug(f"Flipped data: Buy {buy_currency.mnemonic} {buy_amount}, Sell {sell_currency.mnemonic} {sell_amount}")

            # Monex provides the data from their perspective, so we need to flip it
            # The currency they're giving us is what we're buying, and what they're selling
            fxpair, side = determine_rate_side(sell_currency, buy_currency)
            market_name = fxpair.market

            logger.debug(f"After determine_rate_side: fxpair={fxpair}, side={side}")

            # Determine lock side (usually the non-USD side)
            lock_side = sell_currency if sell_currency.mnemonic != 'USD' else buy_currency

            logger.debug(f"Determined lock_side: {lock_side.mnemonic}")

            # Assign done and cntr_done based on side
            if side == 'Buy':
                done = buy_amount
                cntr_done = sell_amount
            else:  # side == 'Sell'
                done = sell_amount
                cntr_done = buy_amount

            logger.debug(f"Assigned done={done}, cntr_done={cntr_done}")

            logger.info(f'{market_name} {side} Lock: {lock_side.mnemonic} Done: {done} Cntr: {cntr_done}')
            rate = float(order_details['displayRate'])

            transaction_date = MonexApi.parse_datetime(order['entryDate'])
            value_date = MonexApi.parse_datetime(order['valueDate']).date()

            purpose_of_payment = None
            beneficiaries = None
            settlement_info = None
            beneid = method = None
            settle_account_id = settle_method = None

            reference = order_details.get('reference')

            if order_details['bene']:
                bene_data = order_details.get('bene')
                try:
                    bene_broker = BeneficiaryBroker.objects.get(
                        beneficiary__company=company,
                        broker_beneficiary_id=bene_data.get('id'),
                        broker=Broker.objects.get(
                            broker_provider=BrokerProviderOption.MONEX)
                    )
                    beneid = bene_broker.beneficiary.beneficiary_id
                    method = bene_broker.beneficiary.preferred_method
                except BeneficiaryBroker.DoesNotExist:
                    logger.error(
                        f'No beneficiary broker found for {company.name} - {company.pk} - {order_details["amountCurrency"]}')

                # TODO: use order_details['bene'] to figure out bene
            if not order['isHolding'] and order['beneNickname']:
                ...
                # TODO: use order['beneNickname'] to figure out bene

            if not beneid and order['isHolding'] and order['beneNickname']:
                generated_nickname = order['beneNickname']
                bene_pattern = r'^(.*?)-(.*?)-(\d+)$'
                match = re.match(bene_pattern, generated_nickname)

                if match:
                    account_type, currency, account_number = match.groups()
                    logger.debug(
                        f"Extracted bene info: Account Type: {account_type}, Currency: {currency}, Account Number: {account_number}")
                    if account_type == 'Operating Account':
                        try:
                            wallet = Wallet.objects.get(
                                type=Wallet.WalletType.WALLET,
                                currency__mnemonic=currency,
                                company=company,
                                broker__broker_provider=BrokerProviderOption.MONEX
                            )
                            beneid = wallet.wallet_id
                            method = Beneficiary.PaymentSettlementMethod.WALLET
                        except Wallet.DoesNotExist:
                            logger.error(
                                f'No wallet found for {company.name} - {company.pk} - {order_details["amountCurrency"]}')

            if not beneid:
                if order['isHolding']:
                    beneid, method = check_single_wallet(
                        company, buy_currency)

                else:
                    beneid, method = check_single_bene(
                        company, buy_currency)

            if not settle_account_id:
                settle_account_id, settle_method = check_single_sa(
                    company, sell_currency)

            if beneid:
                if beneid:
                    beneficiaries = [
                        {"beneficiary_id": beneid, "method": method, "purpose_of_payment": purpose_of_payment}]

            if settle_account_id:
                settlement_info = [{"settlement_account_id": settle_account_id,
                                    "method": settle_method, "payment_reference": reference}]

            # ========================================

            instrument_type = tenor = 'spot'

            internal_state = INTERNAL_STATES.DONE
            external_state = EXTERNAL_STATES.DONE
            phase = PHASES.RECON

            # Prepare payment data
            payment_data = {
                'company': company,
                'name': f'{company.name}: {market_name}',
                'amount': buy_amount,
                'cntr_amount': sell_amount,
                'buy_currency': buy_currency.mnemonic,
                'sell_currency': sell_currency.mnemonic,
                'lock_side': lock_side.mnemonic,
                'delivery_date': value_date,
                'payment_status': Payment.PaymentStatus.DELIVERED if value_date <= date.today() else Payment.PaymentStatus.BOOKED,
                'execution_timing': 'immediate',
                'payment_ident': order_number,
                'purpose_of_payment': purpose_of_payment,
                'origin_account_id': settle_account_id,
                'origin_account_method': settle_method,
                'destination_account_id': beneid,
                'destination_account_method': method,
            }

            # Create or update payment using the service
            if payment:
                payment = PaymentService.update_payment(payment, **payment_data)
                logger.info(f"Updated existing payment for order {order_number}")
            else:
                payment = PaymentService.create_payment(**payment_data)
                logger.info(f"Created new payment for order {order_number}")

            # Update ticket data
            ticket_data = {
                'company': company,
                'amount': done,
                'sell_currency': sell_currency,
                'buy_currency': buy_currency,
                'fxpair': fxpair,
                'market_name': market_name,
                'side': side,
                'lock_side': lock_side,
                'tenor': tenor,
                'value_date': value_date,
                'transaction_time': transaction_date,
                'cashflow_id': payment.cashflow_generator.cashflows.first().id,
                'instrument_type': instrument_type,
                'time_in_force': 'gtc',
                'ticket_type': 'payment',
                'action': 'execute',
                'execution_strategy': 'market',
                'done': done,
                'cntr_done': cntr_done,
                'external_quote': rate,
                'rate': rate,
                'all_in_done': done,
                'all_in_rate': rate,
                'all_in_cntr_done': cntr_done,
                'broker_id': order_number,
                'broker': 'MONEX',
                'draft': False,
                'with_care': False,
                'internal_state': internal_state,
                'external_state': external_state,
                'phase': phase,
                'beneficiaries': beneficiaries,
                'settlement_info': settlement_info,
                'trade_details': order,
            }

            # Create or update ticket
            if ticket:
                for key, value in ticket_data.items():
                    setattr(ticket, key, value)
                ticket.save()
                logger.info(f"Updated existing ticket for order {order_number}")
            else:
                ticket = Ticket.objects.create(ticket_id=str(uuid.uuid4()), **ticket_data)
                logger.info(f"Created new ticket for order {order_number}")

            # Update cashflow with ticket_id if not set
            cashflow = payment.cashflow_generator.cashflows.first()
            if not cashflow.ticket_id:
                cashflow.ticket_id = ticket.ticket_id
                cashflow.save()

    except Exception as e:
        logger.exception(
            f"Unexpected error in backfill_spot_order for company {company.name}: {str(e)}")

# =====================


def check_manual_fill(ticket: Ticket, forward):

    # might need a better check
    if ticket.action == Ticket.Actions.EXECUTE:
        # this will never happen because right now we can't associate a ticket with a deal number
        if ticket.internal_state == INTERNAL_STATES.WORKING and ticket.rfq_type != CnyExecution.RfqTypes.API:

            fwd_id = forward['dealNumber']

            buy_currency = ticket.get_buy_currency()
            sell_currency = ticket.get_sell_currency()
            side = "Sell" if ticket.get_lock_side() == sell_currency else "Buy"

            buy_amount = float(forward['buyAmount'])
            sell_amount = float(forward['sellAmount'])

            rate = all_in_rate = forward['exchangeRate']

            if side == 'Sell':
                done = all_in_done = sell_amount
                cntr_done = all_in_cntr_done = buy_amount
            else:
                done = all_in_done = buy_amount
                cntr_done = all_in_cntr_done = sell_amount

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
            if resave:
                ticket.save()

# ==========


def search_for_matching_ticket(buy_currency, sell_currency, buy_amount, sell_amount, value_date, transaction_date):

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


def check_payment_done(forward, fwd_id, ticket):

    try:
        payment = Payment.objects.get(payment_ident=fwd_id)
    except:
        payment = None

    if payment and payment.payment_status == Payment.PaymentStatus.BOOKED:
        value_date = MonexApi.parse_datetime(forward['valueDate']).date()
        # could also check forward available balance = 0.0?
        if date.today() >= value_date:
            payment.payment_status = Payment.PaymentStatus.DELIVERED
            payment.save()

# ===============================


"""
{'dealNumber': '0411970', 'postTransactionId': 607435,
'entryDate': 1719944231, 'valueDate': 1727720231,
'dealType': 'Window Forward', 'exchangeRate': '1.08990000', 'status': True, 'statusStr': 'open',
'buyCurrency': 'USD', 'buyAmount': '16348.50', 'buyBalance': '16348.50',
'sellCurrency': 'EUR', 'sellAmount': '15000.00', 'sellBalance': '15000.00',
'cashDepositAmount': '0.00', 'entityName': 'Pangea Parent Entity',
'drawdownAvailable': True, 'drawdownNotAvailableMessage': ''}
"""


def backfill_forward(company, forward_id=None, forward=None, only_ndf=False, dry_run=False):
    if forward is None:
        assert forward_id
        # get forward here
        raise NotImplementedError

    fwd_id = forward['dealNumber']

    try:
        with transaction.atomic():
            try:
                ticket = Ticket.objects.get(broker_id=fwd_id)
                logger.info(f'Ticket found with forward id: {fwd_id}')
            except Ticket.DoesNotExist:
                ticket = None
                logger.info(
                    f'No ticket found with forward id: {fwd_id}... creating new ticket')

            try:
                payment = Payment.objects.get(payment_ident=fwd_id)
                logger.info(f'Payment found with forward id: {fwd_id}')
            except Payment.DoesNotExist:
                payment = None
                logger.info(
                    f'No payment found with forward id: {fwd_id}... creating new payment')

            if dry_run:
                return

            # Flip the currencies and amounts to match our perspective
            sell_currency = parse_currency(forward['buyCurrency'])
            buy_currency = parse_currency(forward['sellCurrency'])
            sell_amount = float(forward['buyAmount'])
            buy_amount = float(forward['sellAmount'])


            if buy_currency is None or sell_currency is None:
                logger.error(f"Missing buy or sell currency for forward {fwd_id}. Deleting associated data if exists.")
                if ticket:
                    ticket.delete()
                if payment:
                    payment.delete()
                return

            if buy_currency == sell_currency:
                logger.info(f"Same buy and sell currency for forward {fwd_id}. Deleting associated data if exists.")
                if ticket:
                    ticket.delete()
                if payment:
                    payment.delete()
                return

            logger.debug(f"Flipped data: Buy {buy_currency.mnemonic} {buy_amount}, Sell {sell_currency.mnemonic} {sell_amount}")
            
            transaction_date = MonexApi.parse_datetime(forward['entryDate'])
            value_date = MonexApi.parse_datetime(forward['valueDate']).date()

            # Monex provides the data from their perspective, so we need to flip it
            # The currency they're giving us is what we're buying, and what they're selling
            fxpair, side = determine_rate_side(sell_currency, buy_currency)
            market_name = fxpair.market

            logger.debug(f"After determine_rate_side: fxpair={fxpair}, side={side}")

            # Determine lock side (usually the non-USD side)
            lock_side = sell_currency if sell_currency.mnemonic != 'USD' else buy_currency

            logger.debug(f"Determined lock_side: {lock_side.mnemonic}")

            # Assign done and cntr_done based on side
            if side == 'Buy':
                done = buy_amount
                cntr_done = sell_amount
            else:  # side == 'Sell'
                done = sell_amount
                cntr_done = buy_amount

            logger.debug(f"Assigned done={done}, cntr_done={cntr_done}")

            logger.info(f'{market_name} {side} Lock: {lock_side.mnemonic} Done: {done} Cntr: {cntr_done}')
            rate = all_in_rate = float(forward['exchangeRate'])

            if forward['dealType'] == 'Fixed Dated Forward':
                instrument_type = tenor = 'fwd'
            elif forward['dealType'] == 'Window Forward':
                instrument_type = 'window_fwd'
                tenor = 'fwd'
            else:
                logger.error(f'New kind of instrument: {forward["dealType"]}')
                instrument_type = tenor = None

            purpose_of_payment = None
            beneid = reference = method = None
            settle_account_id = settle_method = None
            beneficiaries = None
            settlement_info = None

            if not beneid:
                beneid, method = check_single_bene(company, buy_currency)

            if not beneid:
                beneid, method = check_single_wallet(company, buy_currency)

            if not settle_account_id:
                settle_account_id, settle_method = check_single_sa(
                    company, sell_currency)

            if beneid:
                beneficiaries = [
                    {"beneficiary_id": beneid, "method": method, "purpose_of_payment": purpose_of_payment}]

            if settle_account_id:
                settlement_info = [{"settlement_account_id": settle_account_id,
                                    "method": settle_method, "payment_reference": reference}]

            logger.info(f'Syncing forward: {fwd_id}, {transaction_date}')

            payment_status = Payment.PaymentStatus.BOOKED if value_date > date.today(
            ) else Payment.PaymentStatus.DELIVERED

            # Prepare payment data
            payment_data = {
                'company': company,
                'name': f'{company.name}: {fwd_id}',
                'amount': buy_amount,
                'cntr_amount': sell_amount,
                'buy_currency': buy_currency.mnemonic,
                'sell_currency': sell_currency.mnemonic,
                'lock_side': lock_side.mnemonic,
                'delivery_date': value_date,
                'payment_status': payment_status,
                'execution_timing': 'immediate',
                'payment_ident': fwd_id,
                'purpose_of_payment': purpose_of_payment,
                'origin_account_id': settle_account_id,
                'origin_account_method': settle_method,
                'destination_account_id': beneid,
                'destination_account_method': method,
            }

            # Create or update payment using the service
            if payment:
                payment = PaymentService.update_payment(payment, **payment_data)
                logger.info(f"Updated existing payment for forward {fwd_id}")
            else:
                payment = PaymentService.create_payment(**payment_data)
                logger.info(f"Created new payment for forward {fwd_id}")

            # Prepare ticket data
            ticket_data = {
                'company': company,
                'amount': done,
                'sell_currency': sell_currency,
                'buy_currency': buy_currency,
                'fxpair': fxpair,
                'market_name': market_name,
                'side': side,
                'lock_side': lock_side,
                'tenor': tenor,
                'value_date': value_date,
                'transaction_time': transaction_date,
                'cashflow_id': payment.cashflow_generator.cashflows.first().id,
                'instrument_type': instrument_type,
                'time_in_force': 'gtc',
                'ticket_type': 'payment',
                'action': 'execute',
                'execution_strategy': 'market',
                'done': done,
                'cntr_done': cntr_done,
                'external_quote': all_in_rate,
                'rate': rate,
                'all_in_done': done,
                'all_in_rate': all_in_rate,
                'all_in_cntr_done': cntr_done,
                'broker_id': fwd_id,
                'broker': 'MONEX',
                'draft': False,
                'with_care': False,
                'internal_state': INTERNAL_STATES.DONE,
                'external_state': EXTERNAL_STATES.DONE,
                'phase': PHASES.RECON,
                'beneficiaries': beneficiaries,
                'settlement_info': settlement_info,
                'trade_details': forward,
            }

            # Create or update ticket
            if ticket:
                for key, value in ticket_data.items():
                    setattr(ticket, key, value)
                ticket.save()
            else:
                ticket = Ticket.objects.create(
                    ticket_id=str(uuid.uuid4()), **ticket_data)

            # Update cashflow with ticket_id if not set
            cashflow = payment.cashflow_generator.cashflows.first()
            if not cashflow.ticket_id:
                cashflow.ticket_id = ticket.ticket_id
                cashflow.save()

    except Exception as e:
        logger.exception(
            f"Unexpected error in backfill_forward for company {company.name}: {str(e)}")

# ===========================


def get_inferred_company(monex_company_name):
    try:
        company = Company.objects.get(
            monexcompanysettings__entity_name=monex_company_name)
        return company
    except Company.DoesNotExist:
        return None


def get_company_by_entity_id(entity_id):
    try:
        company = Company.objects.get(
            monexcompanysettings__entity_id=entity_id)
        return company
    except Company.DoesNotExist:
        return None


def backfill_forwards(company=None, only_ndf=False, dry_run=True):
    try:
        if company:
            try:
                if not company.monexcompanysettings:
                    logger.info(
                        f"Company {company.name} has no Monex settings. Skipping.")
                    return
            except ObjectDoesNotExist:
                logger.info(
                    f"Company {company.name} has no Monex settings. Skipping.")
                return
        logger.info(f'backfilling forwards for company {company.name}')
        monex_api = MonexApi.init()

        try:
            forwards = monex_api.get_all_forwards(company=company)
        except MonexAPIException as e:
            logger.error(f'Problem getting Monex forwards: {str(e)}')
            return

        if forwards:
            for forward in forwards:
                try:
                    if company is None:
                        inferred_company = get_inferred_company(
                            forward['Pangea Parent Entity'])
                        if inferred_company:
                            backfill_forward(
                                inferred_company, forward=forward, only_ndf=only_ndf, dry_run=dry_run)
                    else:
                        if company.monexcompanysettings.company_name != forward['entityName']:
                            continue
                        backfill_forward(company, forward=forward,
                                         only_ndf=only_ndf, dry_run=dry_run)
                except Exception as e:
                    logger.exception(
                        f"Error processing forward {forward.get('dealNumber', 'unknown')}: {str(e)}")

    except Exception as e:
        logger.exception(f"Unexpected error in backfill_forwards: {str(e)}")

# [{'postId': 545108, 'dealNumber': '0411968', 'amount': '10626.00', 'currencyId': 1, 'amountCurrency': 'USD', 'costCurrencyId': 42, 'beneNickname': '', 'isHolding': False, 'iftEntityId': None, 'entryDate': 1719942295, 'valueDate': 1719942295, 'initiated': None, 'funded': None, 'sent': None, 'delivered': None, 'entityName': 'Pangea Parent Entity', 'entityId': 14697, 'entityNumber': '0016283', 'trackingId': 'RCBSSSNHNLZY7Z5M'}]


def backfill_spot_orders(company=None, dry_run=True):
    try:
        if company:
            try:
                if not company.monexcompanysettings:
                    logger.info(
                        f"Company {company.name} has no Monex settings. Skipping.")
                    return
            except ObjectDoesNotExist:
                logger.info(
                    f"Company {company.name} has no Monex settings. Skipping.")
                return
        logger.info(f'backfilling spot orders for company {company.name}')
        monex_api = MonexApi.init()
        try:
            orders = monex_api.get_all_spot_orders(company=company)
        except MonexAPIException as e:
            logger.error(f'Problem getting Monex spot orders: {str(e)}')
            return

        if orders:
            for order in orders:
                try:
                    if company is None:
                        inferred_company = get_company_by_entity_id(
                            order['entityId'])
                        if inferred_company:
                            try:
                                if inferred_company.monexcompanysettings:
                                    backfill_spot_order(
                                        inferred_company, order=order, dry_run=dry_run)
                                else:
                                    logger.info(
                                        f"Inferred company {inferred_company.name} has no Monex settings. Skipping order.")
                            except ObjectDoesNotExist:
                                logger.info(
                                    f"Inferred company {inferred_company.name} has no Monex settings. Skipping order.")
                    else:
                        if int(company.monexcompanysettings.entity_id) != order['entityId']:
                            continue
                        backfill_spot_order(
                            company, order=order, dry_run=dry_run)
                except Exception as e:
                    logger.exception(
                        f"Error processing spot order {order.get('dealNumber', 'unknown')}: {str(e)}")

    except Exception as e:
        logger.exception(f"Unexpected error in backfill_spot_orders: {str(e)}")

# ============================
