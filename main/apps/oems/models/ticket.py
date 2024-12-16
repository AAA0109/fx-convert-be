import uuid

from django.db import models
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import Company
from main.apps.core.constants import VALUE_DATE_HELP_TEXT, LOCK_SIDE_HELP_TEXT
from main.apps.currency.models import Currency
from main.apps.currency.models import FxPair
from main.apps.oems.backend.ticket_shared import TicketBase
from main.apps.oems.backend.utils import DateTimeEncoder
from main.apps.oems.models.cny import CnyExecution
from main.apps.oems.models.extensions import DateTimeWithoutTZField


# ========================================

class Ticket(TimeStampedModel, TicketBase):
    class Meta:
        unique_together = (('transaction_id', 'company',),)
        indexes = [
            models.Index(fields=['ticket_id']),
        ]

    # external id to go back to customer
    ticket_id = models.UUIDField(
        primary_key=False, default=uuid.uuid4, null=False, editable=False
    )

    # Required Fields
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, related_name="payment_requests", null=True, blank=True,
        help_text="Related company associated with the transaction."
    )
    customer_id = models.TextField(
        null=True, blank=True,
        help_text="Identifier for the customer associated with the company for the transaction."
    )  # customer for the company for ultima

    sell_currency = models.ForeignKey(
        Currency, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="from_currency_ticket",
        help_text="The currency being transferred from."
    )
    buy_currency = models.ForeignKey(
        Currency, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="to_currency_ticket",
        help_text="The currency being transferred to."
    )
    amount = models.FloatField(
        help_text="The amount of lock_side currency being transferred in the transaction."
    )
    lock_side = models.ForeignKey(
        Currency, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lock_side_currency_ticket",
        help_text=LOCK_SIDE_HELP_TEXT
    )

    class Tenors(models.TextChoices):
        RTP = 'RTP', 'RTP'
        ON = 'ON', 'ON'
        TN = 'TN', 'TN'
        SPOT = 'spot', 'Spot'
        SN = 'SN', 'SN'
        SW = 'SW', 'SW'
        _1W = '1W', '1W'
        _2W = '2W', '2W'
        _3W = '3W', '3W'
        _1M = '1M', '1M'
        _2M = '2M', '2M'
        _3M = '3M', '3M'
        _4M = '4M', '4M'
        _5M = '5M', '5M'
        _6M = '6M', '6M'
        _7M = '7M', '7M'
        _8M = '8M', '8M'
        _9M = '9M', '9M'
        _1Y = '1Y', '1Y'
        FWD = 'fwd', 'Fwd'
        NDF = 'ndf', 'NDF'

    tenor = models.CharField(
        choices=Tenors.choices, max_length=10, null=True, blank=True,
        help_text="The tenor of the transaction, representing the settlement period."
    )
    value_date = models.DateField(
        help_text=VALUE_DATE_HELP_TEXT
    )

    class Sides(models.TextChoices):
        BUY = 'Buy', 'Buy'
        SELL = 'Sell', 'Sell'
        BUYSELL = 'BuySell', 'BuySell'
        SELLBUY = 'SellBuy', 'SellBuy'
        TRANSFER = 'Transfer', 'Transfer'

    side = models.CharField(choices=Sides.choices, max_length=10, null=True, blank=True)

    fixing_date = models.DateField(null=True, blank=True)
    fixing_time = models.TextField(null=True, blank=True)
    fixing_venue = models.TextField(null=True, blank=True)
    fixing_source = models.TextField(null=True, blank=True)

    draft = models.BooleanField(
        default=False,
        help_text="Specifies whether the transaction is in draft stage or not."
    )

    with_care = models.BooleanField(
        default=False,
        help_text="Specifies whether the transaction should be handled manually by the desk."
    )

    class TimeInForces(models.TextChoices):
        _10SEC = '10sec', '10s'
        _1MIN = '1min', '1min'
        _1HR = '1hr', '1hr'
        _GTC = 'gtc', 'GTC'
        _DAY = 'day', 'DAY'
        _IND = 'indicative', 'INDICATIVE'

    time_in_force = models.CharField(
        choices=TimeInForces.choices, max_length=16,
        help_text="Specifies the duration for which the transaction is valid."
    )

    class TicketTypes(models.TextChoices):
        PAYMENT = 'payment', 'Payment'
        PAYMENT_RFQ = 'payment_rfq', 'Payment RFQ'
        RFQ = 'rfq', 'RFQ'
        EXECUTE = 'execute', 'Execute'
        HEDGE = 'hedge', 'Hedge'

    ticket_type = models.CharField(
        choices=TicketTypes.choices, max_length=32,
        help_text="Specifies the type of transaction, whether it's a payment, RFQ, execute, or hedge."
    )

    class TicketStyle(models.TextChoices):
        PARENT = 'parent', 'parent'
        CHILD = 'child', 'child'
        VIRTUAL_PARENT = 'virtual_parent', 'virtual_parent'
        VIRTUAL_CHILD = 'virtual_child', 'virtual_child'

    style = models.CharField(TicketStyle.choices, max_length=32, null=True, blank=True,
                             help_text="Specifies the ticket style.", default=TicketStyle.PARENT
                             )

    class FundingModel(models.TextChoices):
        PREFUNDED = 'prefunded', 'prefunded'
        POSTFUNDED = 'postfunded', 'postfunded'
        PREMARGINED = 'premargined', 'premargined'
        POSTMARGINED = 'postmargined', 'postmargined'
        FLEXIBLE = 'flexible', 'flexible'

    funding = models.CharField(FundingModel.choices, max_length=32, null=True, blank=True,
                               help_text="Specifies the ticket funding type.", default=FundingModel.POSTFUNDED
                               )
    funding_deadline = DateTimeWithoutTZField(null=True, blank=True)

    account_id = models.TextField(
        null=True, blank=True,
        help_text="Unique identifier for account."
    )

    clearing_account_id = models.TextField(
        null=True, blank=True,
        help_text="Unique identifier for the clearing account."
    )

    # Optional Fields

    cashflow_id = models.TextField(
        null=True, blank=True,
        help_text="Unique identifier for the cashflow. If cashflow_id is provided, required fields are not necessary as they will be filled in appropriately from the cashflow."
    )

    transaction_id = models.TextField(
        null=True, blank=True,
        help_text="Client-supplied unique identifier for the transaction."
    )

    transaction_group = models.TextField(
        null=True, blank=True,
        help_text="Client-supplied identifier to provide transaction grouping."
    )

    start_time = DateTimeWithoutTZField(null=True, blank=True)
    end_time = DateTimeWithoutTZField(null=True, blank=True)
    trigger_time = DateTimeWithoutTZField(null=True, blank=True)
    order_length = models.PositiveIntegerField(null=True, blank=True)

    class DateConvs(models.TextChoices):
        MODF = 'modified_follow', 'Modified Follow'
        REJECT = 'reject', 'Reject'
        NEXT = 'next', 'Next'
        PREV = 'previous', 'Previous'

    date_conversion = models.CharField(choices=DateConvs.choices, null=True, blank=True)

    class ExecutionStrategies(models.TextChoices):
        MARKET = 'market', 'Market'
        LIMIT = 'limit', 'Limit'
        STOP = 'stop', 'Stop'
        TRIGGER = 'trigger', 'Trigger'
        STRATEGIC_EXECUTION = 'strategic_execution', 'Strategic Execution'
        SMART = 'smart', 'SMART'
        BESTX = 'bestx', 'Best Execution'

    class HedgeStrategies(models.TextChoices):
        SELF_DIRECTED = 'self_directed', 'Self-Directed'
        AUTOPILOT = 'autopilot', 'Autopilot'
        PARACHUTE = 'parachute', 'Parachute'
        ZERO_GRAVITY = 'zero_gravity', 'Zero-Gravity'

    execution_strategy = models.CharField(
        choices=ExecutionStrategies.choices,
        null=True, blank=True, max_length=128
    )
    execution_status = models.TextField(null=True, blank=True)

    hedge_strategy = models.TextField(
        choices=HedgeStrategies.choices,
        null=True, blank=True,
        help_text='User-defined hedging strategy'
    )

    hedge_strategy_fields = models.JSONField(
        encoder=DateTimeEncoder,
        null=True, blank=True,
        help_text='Hedging-strategy specific fields. Please see documentation for defaults and customization.'
    )

    broker = models.TextField(null=True, blank=True)
    algo = models.CharField(max_length=128, null=True, blank=True)
    algo_fields = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)

    # differentiate trigger prices between client and ourselves
    upper_trigger = models.FloatField(
        null=True, blank=True,
        help_text="Execution begins when client price goes above this threshold."
    )
    lower_trigger = models.FloatField(
        null=True, blank=True,
        help_text="Execution begins when client price goes below this threshold."
    )
    stop_trigger = models.FloatField(
        null=True, blank=True,
        help_text="Execution will begin when price crosses below this threshold. This is a stop-loss order. This is a resting order."
    )
    limit_trigger = models.FloatField(
        null=True, blank=True,
        help_text="Execution will leave a resting order to execute at a maximum of this price or better. This is a resting order."
    )

    ref_ticket = models.ForeignKey('Ticket', on_delete=models.SET_NULL, null=True, blank=True)
    ref_price = models.FloatField(null=True, blank=True)
    # TODO: fk to user in database?
    trader = models.TextField(null=True, blank=True)

    # Internal Fields
    market_name = models.TextField(null=True, blank=True)

    fxpair = models.ForeignKey(
        FxPair, on_delete=models.SET_NULL, related_name="ticket_fx_pair", null=True, blank=True,
        help_text="FxPair Object Reference"
    )

    # TODO: this is structured settlement information
    beneficiaries = models.JSONField(encoder=DateTimeEncoder,
                                     null=True, blank=True,
                                     help_text='Generic beneficiary and settlement information.'
                                     )

    class Actions(models.TextChoices):
        RFQ = 'rfq', 'RFQ'
        EXECUTE = 'execute', 'Execute'

    class InstrumentTypes(models.TextChoices):
        SPOT = 'spot', 'SPOT'
        FWD = 'fwd', 'FWD',
        NDF = 'ndf', 'NDF',
        WINDOW_FWD = 'window_fwd','WINDOW_FWD'
        OPTIONS_STRATEGY = 'option_strategy', 'OPTION_STRATEGY'
        FUT = 'fut', 'FUT'
        FUT_AS_FWD = 'fut_as_fwd', 'FUT_AS_FWD'
        FWD_THEN_SPOT = 'fwd_then_spot', 'FWD_THEN_SPOT'
        NDF_THEN_SPOT = 'ndf_then_spot', 'NDF_THEN_SPOT'

    action = models.TextField(choices=Actions.choices, null=True, blank=True)
    instrument_type = models.CharField(choices=InstrumentTypes.choices, null=True, blank=True)
    underlying_instrument = models.TextField(null=True, blank=True)
    instrument_fields = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)
    group_id = models.BigIntegerField(null=True, blank=True)
    internal_trader = models.TextField(null=True, blank=True)
    source = models.TextField(null=True, blank=True)
    paused = models.BooleanField(default=False)
    destination = models.TextField(null=True, blank=True)
    sub_destination = models.TextField(null=True, blank=True)
    oms_owner = models.TextField(null=True, blank=True)
    ems_owner = models.TextField(null=True, blank=True)
    last_message_id = models.BigIntegerField(null=True, blank=True)
    exec_broker = models.TextField(null=True, blank=True)
    clearing_broker = models.TextField(null=True, blank=True)
    options_instructions = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)

    # for auth stuff
    # TODO: fk to user in database or null?
    auth_user = models.TextField(null=True, blank=True)
    auth_time = DateTimeWithoutTZField(null=True, blank=True)

    # quote stuff

    rfq_type = models.TextField(choices=CnyExecution.RfqTypes.choices, null=True, blank=True)
    external_quote = models.FloatField(null=True, blank=True)
    internal_quote = models.FloatField(null=True, blank=True)
    internal_quote_id = models.TextField(null=True, blank=True)
    external_quote_id = models.TextField(null=True, blank=True)

    class RfqType(models.TextChoices):
        API = 'api', 'API'
        MANUAL = 'manual', 'MANUAL'
        UNSUPPORTED = 'unsupported', 'UNSUPPORTED'
        INDICATIVE = 'indicative', 'INDICATIVE'
        NORFQ = 'norfq', 'NORFQ'

    quote_type = models.CharField(choices=RfqType.choices, max_length=16, null=True, blank=True)
    quote_source = models.TextField(null=True, blank=True)
    quote_user = models.TextField(null=True, blank=True)
    quote_fee = models.FloatField(null=True, blank=True)
    quote_indicative = models.BooleanField(default=False)
    external_quote_expiry = DateTimeWithoutTZField(null=True, blank=True)
    internal_quote_expiry = DateTimeWithoutTZField(null=True, blank=True)
    internal_quote_info = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)
    broker_id = models.TextField(null=True, blank=True, )
    broker_state = models.TextField(null=True, blank=True, )
    broker_state_start = DateTimeWithoutTZField(null=True, blank=True)

    # state machine stuff

    class Phases(models.TextChoices):
        PRETRADE = 'PRETRADE', 'Pretrade'
        TRADE = 'TRADE', 'Trade'
        SETTLE = 'SETTLE', 'Settle'
        RECON = 'RECON', 'Recon'

    # ONCE STATE MACHINE IS CLEAR FINALIZE IT HERE

    phase = models.CharField(choices=Phases.choices, max_length=64, null=True, blank=True)
    internal_state = models.CharField(max_length=64, null=True, blank=True)
    external_state = models.CharField(max_length=64, null=True, blank=True)
    internal_state_start = DateTimeWithoutTZField(null=True, blank=True)
    external_state_start = DateTimeWithoutTZField(null=True, blank=True)

    # accounting
    remaining_qty = models.FloatField(null=True, blank=True)  # TODO this defaults to amount
    done = models.FloatField(default=0.0, null=True, blank=True)
    cntr_done = models.FloatField(default=0.0, null=True, blank=True)

    # reference rates
    spot_rate = models.FloatField(null=True, blank=True)
    fwd_points = models.FloatField(null=True, blank=True)
    rate = models.FloatField(null=True, blank=True)

    all_in_done = models.FloatField(default=0.0, null=True, blank=True)
    all_in_cntr_done = models.FloatField(default=0.0, null=True, blank=True)
    all_in_rate = models.FloatField(null=True, blank=True)

    penalty = models.FloatField(default=0.0, null=True, blank=True)
    fee_avg_price = models.FloatField(null=True, blank=True)
    fee = models.FloatField(default=0.0, null=True, blank=True)
    fee_cntr = models.FloatField(default=0.0, null=True, blank=True)
    commission = models.FloatField(default=0.0, null=True, blank=True)
    commission_ccy = models.CharField(max_length=8, null=True, blank=True)
    delivery_fee = models.FloatField(default=0.0, null=True, blank=True)
    delivery_fee_unit = models.CharField(max_length=8, null=True, blank=True)

    transaction_time = DateTimeWithoutTZField(null=True, blank=True)

    # mark to market stuff
    mark_to_market = models.FloatField(null=True, blank=True)
    last_mark_time = DateTimeWithoutTZField(null=True, blank=True)
    mtm_info = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)

    # notes + tags stuff for nice querying
    notes = models.TextField(null=True, blank=True)
    payment_memo = models.TextField(null=True, blank=True, help_text='Internal free-form payment memo.')
    error_message = models.TextField(null=True, blank=True)
    tags = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)

    # Settlement
    settlement_amount = models.FloatField(null=True, blank=True)
    settlement_rate = models.FloatField(null=True, blank=True)
    settlement_all_in_rate = models.FloatField(null=True, blank=True)
    settlement_fee = models.FloatField(null=True, blank=True)
    settlement_allocated = models.FloatField(null=True, blank=True)
    settlement_unallocated = models.FloatField(null=True, blank=True)
    settlement_info = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)
    mass_payment_info = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)

    recon_info = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)
    trade_details = models.JSONField(encoder=DateTimeEncoder, null=True, blank=True)

    # retry settlement attempt
    settlement_attempt = models.IntegerField(null=True, default=0, help_text='Settlement retry attempt')

    # ===================

    @classmethod
    def _create(cls, **kwargs):
        from main.apps.oems.validators.ticket import shared_ticket_validation
        # validate here
        # set default fields
        kwargs = shared_ticket_validation(kwargs)
        return cls(**kwargs)

    # ===================

    EXPORT_BLACKLIST = {'update_modified'}

    def as_django_model(self) -> 'Ticket':
        return self

    def export(self):
        return {k: v for k, v in vars(self).items() if not k.startswith('_') and k not in self.EXPORT_BLACKLIST}

    def print(self):
        for k, v in vars(self).items():
            if not k.startswith('_') and k not in self.EXPORT_BLACKLIST:
                print(k, v)
