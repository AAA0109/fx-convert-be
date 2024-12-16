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



from main.apps.account.models import Company
from main.apps.oems.services import backfill_corpay
from main.apps.oems.services import backfill_monex

# ========

def parse_currency(x):
    return Currency.get_currency(currency=x)


def parse_company(x):
    return Company.objects.get(pk=int(x))


logger = logging.getLogger(__name__)
logging.disable(logging.DEBUG)


# =========


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        pass


MARKETS = set()
FWD_MARKETS = set()
BACKFILL_END_DATE = datetime(2024, 5, 16, 0, 0, 0, 0).replace(tzinfo=None)
BACKFILL_END_DATE_AWARE = datetime(2024, 5, 16, 0, 0, 0, 0, pytz.UTC)


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


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to backfill tickets from corpay"

    def add_arguments(self, parser):
        self.add_default_arguments(parser)
        parser.add_argument('--company-id', type=parse_company, required=False)
        parser.add_argument('--all-companies', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--show', action='store_true')
        parser.add_argument('--fwds', action='store_true')
        parser.add_argument('--spot', action='store_true')
        parser.add_argument('--corpay', action='store_true', default=False)
        parser.add_argument('--monex', action='store_true', default=False)

    def do_action(self, company, do_fwds, do_spot, dry_run, show=False):

        logger.info(f'backfilling: {company.name} {company.id}')

        corpay_api = CorPayExecutionServiceFactory.for_company(company)

        try:
            forwards = corpay_api.list_forwards() if do_fwds else None
        except:
            logger.error(f'problem getting corpay credentials for {company.id}')
            forwards = None

        spot_orders = SpotRate.objects.filter(order_number__isnull=False, company_id=company.id).order_by(
            'created') if do_spot else None

        if not forwards and not spot_orders:
            logger.info('no forwards or spot orders found')
            return

        if spot_orders:

            BLACKLIST = {'25157622', '25142795', '25134731', '25100008'}

            for spot_order in spot_orders:

                order_number = spot_order.order_number

                if order_number in BLACKLIST:
                    if show: print('skipping MP order', order_number)
                    continue

                buy_currency = spot_order.payment_currency
                sell_currency = spot_order.settlement_currency
                lock_side = sell_currency if spot_order.rate_lockside == 'Settlement' else buy_currency

                fxpair, side = determine_rate_side(sell_currency, buy_currency)
                market_name = fxpair.market

                MARKETS.add(market_name)

                if spot_order.rate_lockside == 'Settlement':
                    amount = spot_order.settlement_amount
                    cost_amount = spot_order.payment_amount
                else:
                    amount = spot_order.payment_amount
                    cost_amount = spot_order.settlement_amount

                if side == 'Sell':
                    rate = all_in_rate = 1.0 / spot_order.rate_value
                else:
                    rate = all_in_rate = spot_order.rate_value

                transaction_date = spot_order.created
                value_date = spot_order.created.date() + timedelta(days=2)

                if transaction_date >= BACKFILL_END_DATE_AWARE:
                    continue

                if dry_run:
                    if show: print('adding spot order:', order_number)
                    continue

                # ================
                # add payment here

                print('syncing spot transaction:', order_number, transaction_date)

                purpose_of_payment = None
                beneficiaries = None
                settlement_info = None
                beneid = reference = method = None
                settle_account_id = settle_method = None

                try:
                    order_details = corpay_api.get_order_details(order_number)
                    beneid = order_details['payments'][0]['beneId']
                    reference = order_details['payments'][0]['reference']
                    method = order_details['payments'][0]['method']
                    settle_account_id = order_details['settlements'][0]['accountId']
                    settle_method = order_details['settlements'][0]['method'][0]
                except:
                    order_details = None

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

                if value_date > date.today():
                    payment_status = Payment.PaymentStatus.BOOKED
                else:
                    payment_status = Payment.PaymentStatus.DELIVERED

                try:
                    payment = Payment.objects.get(payment_ident=order_number)
                except:
                    payment = None

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
                    payment_ident=order_number,
                    purpose_of_payment=purpose_of_payment,
                    origin_account_id=settle_account_id,
                    origin_account_method=settle_method,
                    destination_account_id=beneid,
                    destination_account_method=method,
                )

                if payment is None:
                    payment = PaymentService.create_payment(
                        **payment_info,
                    )
                else:
                    resave = False
                    for k, v in payment_info.items():
                        if hasattr(payment, k) and getattr(payment, k) != v:
                            resave = True
                            setattr(payment, k, v)
                    if resave: payment.save()

                if payment.cashflow_generator.cashflows.count() != 1:
                    raise ValueError

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

                internal_state = INTERNAL_STATES.DONE
                external_state = EXTERNAL_STATES.DONE
                phase = PHASES.RECON

                try:
                    ticket = Ticket.objects.get(broker_id=order_number)
                except:
                    ticket = None

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
                    done=done,
                    cntr_done=cntr_done,
                    external_quote=all_in_rate,
                    rate=rate,
                    all_in_done=all_in_done,
                    all_in_rate=all_in_rate,
                    all_in_cntr_done=all_in_cntr_done,
                    broker_id=order_number,
                    broker='CORPAY',
                    draft=False,
                    with_care=False,
                    internal_state=internal_state,
                    external_state=external_state,
                    phase=phase,
                    beneficiaries=beneficiaries,
                    settlement_info=settlement_info,
                )

                if ticket is None:
                    ticket = Ticket(
                        ticket_id=tid,
                        **ticket_info,
                    )
                    ticket.save()
                else:
                    resave = False
                    for k, v in ticket_info.items():
                        if hasattr(ticket, k) and getattr(ticket, k) != v:
                            resave = True
                            setattr(ticket, k, v)
                    if resave: ticket.save()

                if not cashflow.ticket_id:
                    cashflow.ticket_id = ticket.ticket_id
                    cashflow.save()

        if forwards:

            for forward in forwards['data']['rows']:

                if forward['statusDesc'] in ('Incomplete ', 'Incomplete'):
                    # logger.info(f'skipping forward: {forward["forwardId"]}')
                    continue
                elif 'Unavailable' in forward['statusDesc']:
                    ...
                elif 'Available' not in forward['statusDesc']:
                    print('weird forward:', forward)
                    continue

                links = forward.pop('links')
                if not links:
                    # logger.info(f'skipping forward: {forward["forwardId"]}')
                    continue

                deal_number = forward['deal']
                order_number = forward['ordNum']
                fwd_id = forward['forwardId'] or forward['ordNum']

                buy_currency = parse_currency(forward['currency'])
                sell_currency = parse_currency(forward['costCurrency'])

                fxpair, side = determine_rate_side(sell_currency, buy_currency)
                market_name = fxpair.market

                FWD_MARKETS.add(market_name)

                amount = forward['amount']
                cost_amount = forward['costAmount']

                if str(amount).split('.')[-1] == '0':
                    lock_side = buy_currency
                elif str(cost_amount).split('.')[-1] == '0':
                    lock_side = sell_currency
                else:
                    print('no obvious lockside', forward)
                    lock_side = buy_currency

                if side == 'Sell':
                    rate = all_in_rate = 1.0 / forward['rate']
                else:
                    rate = all_in_rate = forward['rate']

                transaction_date = parse_datetime(forward['dealDate'])
                value_date = parse_datetime(forward['maturityDate']).date()

                if transaction_date >= BACKFILL_END_DATE:
                    continue

                # ================
                # add payment here

                purpose_of_payment = None
                order_details = None
                beneid = reference = method = None
                settle_account_id = settle_method = None
                beneficiaries = None
                settlement_info = None

                try:
                    raise
                    # order_details = corpay_api.get_forward_details(fwd_id)
                    order_details = corpay_api.get_order_details(order_number)
                    frd = corpay_api.get_forward_details(fwd_id)
                    breakpoint()
                    if not order_details['payments']: raise
                    beneid = order_details['payments'][0]['beneId']
                    reference = order_details['payments'][0]['reference']
                    method = order_details['payments'][0]['method']
                    settle_account_id = order_details['settlements'][0]['accountId']
                    settle_method = order_details['settlements'][0]['method'][0]
                    purpose_of_payment = None
                except KeyError:
                    raise
                except:
                    ...

                try:
                    fwd = Forward.objects.get(order_number=order_number)
                    print('found fwd:', order_number)
                    purpose_of_payment = fwd.purpose_of_payment
                    if not settle_account_id:
                        settlement_account_id = fwd.funding_account
                    if not beneid:
                        beneid = fwd.destination_account
                    if not method:
                        method = fwd.destination_account_type
                    if not settle_method:
                        ...
                except:
                    ...

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

                if dry_run:
                    if show: print('adding forward:', fwd_id, transaction_date)
                    continue

                print('syncing forward:', fwd_id, deal_number, order_number, transaction_date)

                if value_date > date.today():
                    payment_status = Payment.PaymentStatus.BOOKED
                else:
                    payment_status = Payment.PaymentStatus.DELIVERED

                try:
                    payment = Payment.objects.get(payment_ident=fwd_id)
                except:
                    payment = None

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

                if payment is None:
                    payment = PaymentService.create_payment(
                        **payment_info,
                    )
                else:
                    resave = False
                    for k, v in payment_info.items():
                        if hasattr(payment, k) and getattr(payment, k) != v:
                            resave = True
                            setattr(payment, k, v)
                    if resave: payment.save()

                if payment.cashflow_generator.cashflows.count() != 1:
                    raise ValueError

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

                try:
                    ticket = Ticket.objects.get(broker_id=fwd_id)
                except:
                    ticket = None

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

                if ticket is None:
                    ticket = Ticket(
                        ticket_id=tid,
                        **ticket_info,
                    )
                    ticket.save()
                else:
                    resave = False
                    for k, v in ticket_info.items():
                        if hasattr(ticket, k) and getattr(ticket, k) != v:
                            resave = True
                            setattr(ticket, k, v)
                    if resave: ticket.save()

                if not cashflow.ticket_id:
                    cashflow.ticket_id = ticket.ticket_id
                    cashflow.save()

    # =======

    def handle(self, *args, **options):

        company = options['company_id']
        all_companies = options['all_companies']
        do_fwds = options['fwds']
        do_spot = options['spot']
        dry_run = options['dry_run']
        show = options['show']

        if all_companies:
            for company in Company.objects.all():
                self.do_action(company, do_fwds, do_spot, dry_run, show=show)
            print('added spot orders in:', sorted(list(MARKETS)))
            print('added fwd orders in:', sorted(list(FWD_MARKETS)))
        elif company:
            self.do_action(company, do_fwds, do_spot, dry_run, show=show)
            print('added spot orders in:', sorted(list(MARKETS)))
            print('added fwd orders in:', sorted(list(FWD_MARKETS)))
        else:
            raise ValueError
