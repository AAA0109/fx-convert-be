import logging
import traceback
from datetime import datetime, date

from django.conf import settings
from hdlib.DateTime.Date import Date

from main.apps.account.models.company import Company
from main.apps.account.models.user import User
from main.apps.core.models.config import Config
from main.apps.core.utils.slack import send_message_to_slack
from main.apps.currency.models import Currency
from main.apps.marketdata.models import IrCurve
from main.apps.marketdata.services.fx.fx_provider import CachedFxSpotProvider, FxForwardProvider
from main.apps.marketdata.services.ir.ir_provider import MdIrProviderService
from main.apps.notification.services.email_service import send_email
from main.apps.oems.backend.date_utils import check_after, now
from main.apps.oems.backend.fields import CONFIRMATION_FIELDS, CONFIRMATION_NDF_FIELDS
from main.apps.oems.backend.fields import RFQ_RETURN_FIELDS, EXECUTE_RETURN_FIELDS
from main.apps.oems.backend.states import INTERNAL_STATES
from main.apps.oems.backend.webhook import WEBHOOK_EVENTS
from main.apps.oems.models.life_cycle import LifeCycleEvent
from main.apps.oems.signals import oems_ticket_external_state_change, oems_ticket_internal_state_change
from main.apps.webhook.models.webhook import Webhook

logger = logging.getLogger(__name__)


class TicketBase:
    ROUND_FACTOR = 10
    MODIFY_ORDER_FIELDS = ['amount', 'algo', 'time_in_force',
                           'start_time', 'end_time', 'order_length', 'paused']
    MODIFY_SETTLE_FIELDS = []
    DJANGO_MODEL_NAME = 'oems_ticket'
    SYNC_FLDS = None
    DATETIME_FLDS = {'start_time', 'end_time', 'external_quote_expiry',
                     'internal_quote_expiry'}  # value_date, internal_state_start, external_state_start
    _db = None
    fwd_provider = None

    # ==================

    def life_cycle_event(self, message: str):
        company = self.get_company()
        event = LifeCycleEvent(
            ticket_id=self.ticket_id,
            company=company,
            trader=self.trader,
            market_name=self.market_name,
            side=self.side,
            cashflow_id=self.cashflow_id,
            transaction_id=self.transaction_id,
            transaction_group=self.transaction_group,
            customer_id=self.customer_id,
            text=message,
        )
        event.save()
        if settings.OEMS_TRACING:
            trader = self.get_trader_email()
            msg = f'{trader} for {company.name} @ {self.broker} :: {self.ticket_id} :: {message}'
            child_msg = '\n'.join(
                f'{k}: {v}' for k, v in self.export().items() if v is not None)
            # TODO: this should use celery
            send_message_to_slack(
                msg, child_message=child_msg, channel=settings.SLACK_NOTIFICATIONS_CHANNEL)

    def export(self):
        return {k: v for k, v in vars(self).items() if not k.startswith('_')}

    def export_fields(self, fields, ignore_nulls=False):
        if isinstance(fields, dict):
            return {v or k: getattr(self, k) for k, v in fields.items() if
                    hasattr(self, k) and (not ignore_nulls or getattr(self, k) is not None)}
        return {k: getattr(self, k) for k in fields if
                hasattr(self, k) and (not ignore_nulls or getattr(self, k) is not None)}

    # ========================================

    @staticmethod
    def calc_amount(rate: float, amount: float, side, currency: Currency, lock_side: Currency):
        if not isinstance(rate, float):
            return None
        unit = int(currency.unit) if isinstance(
            currency.unit, (float, int)) else 2
        if side == 'Sell' and currency.mnemonic != lock_side.mnemonic:
            return round(amount / rate, unit)
        elif side == 'Sell' and currency.mnemonic == lock_side.mnemonic:
            return round(amount * rate, unit)
        elif side == 'Buy' and currency.mnemonic != lock_side.mnemonic:
            return round(amount / rate, unit)
        else:
            return round(amount * rate, unit)

    def get_payment_amounts(self, use_lock_side=False):

        rate = self.all_in_rate or self.external_quote

        ret = {
            'amount': None,
            'cntr_amount': None,
            'rate': rate,
        }

        if self.quote_indicative and not self.all_in_done:
            buy_currency = self.get_buy_currency()
            sell_currency = self.get_sell_currency()
            lock_side = self.get_lock_side()
            if buy_currency.mnemonic == lock_side.mnemonic:
                payment_amount = self.amount
                all_in_cost = self.calc_amount(
                    rate, self.amount, self.side, sell_currency, lock_side)
                ret['amount'] = payment_amount
                ret['cntr_amount'] = all_in_cost
            else:
                payment_amount = self.calc_amount(
                    rate, self.amount, self.side, buy_currency, lock_side)
                all_in_cost = self.amount
                ret['amount'] = all_in_cost
                ret['cntr_amount'] = payment_amount
            return ret

        if use_lock_side:
            buy_currency = self.get_buy_currency()
            lock_side = self.get_lock_side()
            if self.side == 'Sell':
                all_in_cost = self.all_in_done
                payment_amount = self.all_in_cntr_done
            else:
                all_in_cost = self.all_in_cntr_done
                payment_amount = self.all_in_done
            if buy_currency.mnemonic == lock_side.mnemonic:
                ret['amount'] = payment_amount
                ret['cntr_amount'] = all_in_cost
            else:
                ret['amount'] = all_in_cost
                ret['cntr_amount'] = payment_amount
        else:
            if self.side == 'Sell':
                ret['cntr_amount'] = self.all_in_done  # cost
                ret['amount'] = self.all_in_cntr_done  # payment amount
            else:
                ret['cntr_amount'] = self.all_in_cntr_done  # cost
                ret['amount'] = self.all_in_done  # payment amount

        return ret

    def export_rfq(self):
        data = self.export_fields(RFQ_RETURN_FIELDS)
        info = self.get_payment_amounts()
        all_in_cost = info['cntr_amount']
        payment_amount = info['amount']
        if self.delivery_fee_unit != 'USD':
            ...  # todo convert here
        data['transaction_amount'] = payment_amount
        data['total_cost'] = all_in_cost + \
            data['delivery_fee'] if all_in_cost is not None else None
        return data

    def export_execute(self):
        data = self.export_fields(EXECUTE_RETURN_FIELDS)
        if self.side == 'Sell':
            all_in_cost = self.all_in_done
            payment_amount = self.all_in_cntr_done
        else:
            all_in_cost = self.all_in_cntr_done
            payment_amount = self.all_in_done
        data['payment_amount'] = payment_amount
        if self.delivery_fee_unit != 'USD':
            ...  # todo convert here
        data['total_cost'] = all_in_cost + \
            data['delivery_fee'] if all_in_cost is not None else None
        return data

    # ========================================

    def is_expired(self):
        return self.internal_state == INTERNAL_STATES.EXPIRED or (
            self.external_quote_expiry and check_after(self.external_quote_expiry))

    def change_action(self, new_action):
        if new_action != self.action:
            msg = f'ACTION CHANGE: {self.ticket_id} {new_action} from {self.action}'
            logger.info(msg)
            self.action = new_action
            self.life_cycle_event(msg)

    def change_phase(self, new_phase):
        if new_phase != self.phase:
            logger.info(
                f'PHASE CHANGE: {self.ticket_id} {new_phase} from {self.phase}')
            self.phase = new_phase

    def change_internal_state(self, new_state):
        if new_state != self.internal_state:
            msg = f'INTERNAL STATE CHANGE: {self.ticket_id} {new_state} from {self.internal_state}'
            logger.info(msg)
            self.internal_state = new_state
            self.internal_state_start = now()
            logger.info(
                f"Dispatching django signals - class: {self.__class__} - instance {self.__str__()}  - state: {new_state}")
            oems_ticket_internal_state_change.send(
                sender=self.__class__, instance=self, state=new_state)
            self.life_cycle_event(msg)

    def change_external_state(self, new_state):
        if new_state != self.external_state:
            logger.info(
                f'EXTERNAL STATE CHANGE: {self.ticket_id} {new_state} from {self.external_state}')
            self.external_state = new_state
            self.external_state_start = now()
            oems_ticket_external_state_change.send(
                sender=self.__class__, instance=self, state=new_state)
            if self.internal_state == INTERNAL_STATES.CANCELED:
                self.dispatch_event(WEBHOOK_EVENTS.TICKET_CANCELED)
            else:
                self.dispatch_event(WEBHOOK_EVENTS.TICKET_UPDATED)

    def change_broker_state(self, new_state):
        if new_state != self.broker_state:
            self.broker_state = new_state
            self.broker_state_start = now()

    def get_webhook_fields(self, event_type, user):
        if self.action == 'rfq':
            return RFQ_RETURN_FIELDS
        elif self.action == 'execute':
            return EXECUTE_RETURN_FIELDS
        return None

    def dispatch_event(self, event_type, payload=None, user=None):

        if payload is None:
            fields = self.get_webhook_fields(event_type, user)
            if fields:
                payload = self.export_fields(fields)

        if payload:
            if hasattr(self, 'company'):
                company = self.company
            else:
                company = Company.objects.get(pk=self.company_id)
            Webhook.dispatch_event(company, event_type, payload, user=user)

    # ==============================

    DEFAULT_TENORS = ['SN', '1W', '2W', '3W', '1M',
                      '2M', '3M', '4M', '5M', '6M', '9M', '1Y']

    @classmethod
    def get_fwd_provider(cls):
        if not cls.fwd_provider:
            spot_provider = CachedFxSpotProvider()
            cls.fwd_provider = FxForwardProvider(
                fx_spot_provider=spot_provider)
        return cls.fwd_provider

    def do_mark_to_market(self, pnl_currency=None, spot_rate=None, fwd_rate=None, mark_type='open', disc=None,
                          ref_date=None, tenors=None):

        # choose which side to fix

        if not ref_date:
            ref_date = Date.now()

        if pnl_currency is None:
            pnl_currency = self.market_name[:3]

        domestic = self.market_name[:3]

        # ========

        if isinstance(self.value_date, date):
            value_date = Date.from_datetime_date(self.value_date)
        else:
            value_date = self.value_date

        if isinstance(self.fixing_date, date):
            fixing_date = Date.from_datetime_date(self.fixing_date)
        else:
            fixing_date = self.fixing_date

        # ========

        amount = self.all_in_done
        cntr_amount = self.all_in_cntr_done

        if fwd_rate is None:
            fx_pair = self.market_name
            tenors = tenors or self.DEFAULT_TENORS
            fwd_provider = self.get_fwd_provider()
            curve = fwd_provider.get_forward_bid_ask_curve(
                pair=fx_pair, date=ref_date, tenors=tenors, spot=spot_rate)
            fwd_rate = curve.at_D(date=value_date)
            if not spot_rate:
                spot_rate = curve.spot()

        # if you are before fixing date
        if disc is not None:
            pass
        elif (fixing_date and ref_date < fixing_date) or (
                not fixing_date and ref_date < value_date):
            # Get the discount curve
            ois_curve_id = IrCurve.get_ois_curve_id_for_currency(
                currency=domestic)
            discount = MdIrProviderService.get_discount_curve(
                ir_curve=ois_curve_id, date=ref_date)
            disc = discount.at_D(date=value_date)
        else:
            disc = 1.0

        # Compute the MTM NPV
        npv = cntr_amount / fwd_rate * disc
        side = 1 if self.side == 'Buy' else -1
        mtm = (amount - npv) * side

        if pnl_currency != domestic:
            print("TODO: convert the market native pnl to pnl_currency")
            return None

        # this should be a polymorphic dataclass based on asset type

        return {
            'market_name': self.market_name,
            'mark_type': mark_type,
            'transaction_date': self.transaction_time,
            'value_date': value_date,
            'fixing_date': self.fixing_date,
            'all_in_rate': self.all_in_rate,
            'amount': amount,
            'cntr_amount': cntr_amount,
            'current_fwd_rate': fwd_rate,
            'current_spot_rate': spot_rate,
            'current_fwd_points': (fwd_rate - spot_rate),
            'discount_factor': disc,
            'npv': npv,
            'mark_to_market': mtm,
            'mtm_currency': pnl_currency,
        }

    def spot_equiv_mark_to_market(self, pnl_currency=None, spot_rate=None, ref_date=None):

        if not ref_date:
            ref_date = Date.now()

        if pnl_currency is None:
            pnl_currency = self.market_name[:3]

        domestic = self.market_name[:3]

        value_date = self.value_date
        amount = self.all_in_cntr_done / self.spot_rate
        cntr_amount = self.all_in_cntr_done

        fx_pair = self.market_name
        fwd_provider = self.get_fwd_provider()

        curve = fwd_provider.get_forward_bid_ask_curve(
            pair=fx_pair, date=ref_date, tenors=self.DEFAULT_TENORS, spot=spot_rate)
        
        if spot_rate is None:
            spot_rate = curve.spot()
        
        if fwd_rate is None:
            fwd_rate = curve.at_D(date=value_date)

        # Get the discount factor
        ois_curve_id = IrCurve.get_ois_curve_id_for_currency(currency=domestic)
        discount = MdIrProviderService.get_discount_curve(ir_curve=ois_curve_id, date=ref_date)
        disc = discount.at_D(date=value_date)

        # Compute the MTM NPV
        npv = cntr_amount / fwd_rate * disc
        side = 1 if self.side == 'Buy' else -1
        mtm = (amount - npv) * side

        if pnl_currency != domestic:
            print("TODO: convert the market native pnl to pnl_currency")
            return None

        return {
            'market_name': self.market_name,
            'transaction_date': self.transaction_time,
            'value_date': value_date,
            'fixing_date': self.fixing_date,
            'all_in_rate': self.all_in_rate,
            'spot_amount': amount,
            'cntr_spot_amount': cntr_amount,
            'current_spot_rate': spot_rate,
            'npv': npv,
            'mark_to_market': mtm,
            'mtm_currency': pnl_currency,
        }

    # =========================================================================

    def get_confirmation(self):
        if self.instrument_type == 'ndf':
            return self.export_fields(CONFIRMATION_NDF_FIELDS, ignore_nulls=True)
        return self.export_fields(CONFIRMATION_FIELDS, ignore_nulls=True)

    def get_email_recipients(self):

        recipients = set()

        if settings.OEMS_EMAIL_RECIPIENTS:
            if settings.OEMS_EMAIL_RECIPIENTS[0] == 'DISABLED':
                return
            recipients.update(settings.OEMS_EMAIL_RECIPIENTS)
        else:
            company = self.get_company()
            if company.account_owner and company.account_owner.email not in recipients:
                recipients.add(company.account_owner.email)
            if company.rep and company.rep.email not in recipients:
                recipients.add(company.rep.email)
            try:
                for recipient in company.recipients.all():
                    if recipient.email:
                        recipients.add(recipient.email)
            except:
                traceback.print_exc()
            path = "system/notification/internal_recipients"
            internal_recipients_config = Config.objects.get(path=path)
            try:
                internal_recipients = internal_recipients_config.split(",")
            except:
                internal_recipients = None
            if internal_recipients:
                recipients.update(internal_recipients)

        if recipients:
            return list(recipients)

    # =========================================================================

    def send_email_confirm(self, recipients=None, payload=None, company_name=None, title='TRADE CONFIRMATION'):

        if not recipients:
            return

        if payload is None:
            payload = self.get_confirmation()

        if company_name is None:
            if hasattr(self, 'company'):
                company_name = self.company.name
            else:
                try:
                    company = Company.objects.get(pk=self.company_id)
                    company_name = company.name
                except:
                    company_name = 'N/A'

        try:
            if hasattr(self, 'lock_side'):
                ls = self.lock_side.mnemonic
            else:
                ls = Currency.objects.get(pk=self.lock_side_id).mnemonic
        except:
            ls = ''

        context = {
            'title': title,  # optional
            'company': company_name,
            'operation': f'{self.side.title()} {self.market_name} {self.amount:,.2f} {ls}',
            'date': datetime.now().isoformat(),
            'order_id': str(self.ticket_id),
        }

        logger.info(
            f'sending email confirm via celery: {context} {payload} {recipients}')
        send_email.delay('trade_confirm', context, payload, recipients)

    def send_email_mtm(self, recipients=None, payload=None, title='TRADE MTM'):

        if not recipients:
            return

        if payload is None:
            return

        context = {
            'title': title,  # optional
            'company': self.company.name,
            'operation': f'{self.side.title()} {self.market_name} {self.amount:,.2f} {self.lock_side.mnemonic}',
            'date': datetime.now().isoformat(),
            'order_id': str(self.ticket_id),
        }

        send_email.delay('mtm', context, payload, recipients)

    def send_confirm(self, recipients=None, company_name=None):

        payload = self.get_confirmation()

        if not recipients:
            recipients = self.get_email_recipients()

        logger.info(f'send confirm to ({recipients}) with payload {payload}')

        if recipients:  # get emails here
            self.send_email_confirm(
                recipients, payload=payload, company_name=company_name)

        self.dispatch_event(WEBHOOK_EVENTS.TRADE_CONFIRM, payload=payload)

    def send_mark_to_market(self, payload=None):

        if payload is None:
            # lookup home currency?
            payload = self.mark_to_market(pnl_currency=None, )

        recipients = self.get_email_recipients()
        if recipients:  # get emails here
            self.send_email_mtm(recipients, payload=payload)

        self.dispatch_event(WEBHOOK_EVENTS.TRADE_MTM, payload=payload)

    def send_fixing(self, payload=None):

        # TODO: payload = mark_info
        payload = None

        self.dispatch_event(WEBHOOK_EVENTS.TRADE_FIXING, payload=payload)

    def send_settlement(self):

        # TODO: payload = mark_info
        payload = None
        self.dispatch_event(WEBHOOK_EVENTS.TRADE_SETTLE, payload=payload)

    def get_corpay_lock_side(self):
        if hasattr(self, 'lock_side'):
            return 'payment' if self.lock_side.mnemonic == self.buy_currency.mnemonic else 'settlement'
        else:
            return 'payment' if self.lock_side_id == self.buy_currency_id else 'settlement'

    def get_lock_side(self) -> Currency:
        if hasattr(self, 'lock_side'):
            return self.lock_side
        else:
            return Currency.objects.get(pk=self.lock_side_id)

    def get_buy_currency(self) -> Currency:
        if hasattr(self, 'buy_currency'):
            return self.buy_currency
        else:
            return Currency.objects.get(pk=self.buy_currency_id)

    def get_sell_currency(self) -> Currency:
        if hasattr(self, 'sell_currency'):
            return self.sell_currency
        else:
            return Currency.objects.get(pk=self.sell_currency_id)

    def get_company(self) -> Company:
        if hasattr(self, 'company'):
            company = self.company
        else:
            company = Company.get_company(self.company_id)
        return company

    def get_trader_email(self, return_user=False) -> str:
        ret = ''
        if self.trader is not None:
            try:
                user = User.objects.get(id=self.trader)
                if return_user:
                    return user
                ret = user.email
            except:
                ...
        return ret

    def as_django_model(self):
        raise NotImplemented("as_django_model() not implemented for this")
