import logging

from datetime import date, datetime

from django.db import models
from django.conf import settings

from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.account.models import Company
from main.apps.oems.models import Ticket
from main.apps.currency.models import Currency
from main.apps.currency.models import FxPair

from main.apps.oems.backend.xover import enqueue
from main.apps.oems.backend.webhook import WEBHOOK_EVENTS
from main.apps.oems.backend.states import OMS_API_ACTIONS, INTERNAL_STATES, EXTERNAL_STATES, PHASES, ERRORS
from main.apps.oems.validators.ticket import shared_ticket_validation
from main.apps.core.constants import CURRENCY_HELP_TEXT, LOCK_SIDE_HELP_TEXT, VALUE_DATE_HELP_TEXT
from main.apps.oems.api.serializers.fields import ValueDateField


logger = logging.getLogger(__name__)


@extend_schema_serializer(exclude_fields=['trader','company','ticket_type', 'settlement_info', 'auth_user',
        'market_name','beneficiaries','side','tenor','time_in_force','start_time','end_time',
        'trigger_time','destination','draft','with_care','broker','limit_trigger','stop_trigger',
        'date_conversion','open_date'])
class ExecuteSerializer(serializers.ModelSerializer):

    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),help_text=CURRENCY_HELP_TEXT)
    amount = serializers.FloatField(required=True, min_value=0.01, help_text='The amount of lock_side currency')

    lock_side = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=LOCK_SIDE_HELP_TEXT)

    value_date = ValueDateField(required=True, help_text=VALUE_DATE_HELP_TEXT)

    class ExecuteTicketTypes(models.TextChoices):
        PAYMENT = 'payment', 'Payment'
        HEDGE = 'hedge', 'Hedge'

    ticket_type = serializers.ChoiceField(choices=ExecuteTicketTypes.choices, default=ExecuteTicketTypes.PAYMENT)

    action = serializers.HiddenField(default='execute')

    #draft  = serializers.HiddenField(default=False)
    #with_care = serializers.HiddenField(default=False)
    # destination = serializers.HiddenField(default=None)
    # broker = serializers.HiddenField(default=None)

    class ExecuteTenor(models.TextChoices):
        SPOT = 'spot', 'Spot'
        FWD  = 'fwd', 'Fwd'

    tenor = serializers.ChoiceField(choices=ExecuteTenor.choices, required=False, allow_null=True, default=None)
    date_conversion = serializers.ChoiceField(choices=Ticket.DateConvs.choices, default=Ticket.DateConvs.MODF)

    class ExecuteTimeInForces(models.TextChoices):
        _GTC = 'gtc', 'Gtc'
        _DAY = 'day', 'Day'

    time_in_force = serializers.ChoiceField(choices=ExecuteTimeInForces.choices, default=ExecuteTimeInForces._GTC)

    class ExecuteExecutionStrategies(models.TextChoices):
        MARKET = 'market', 'Market - execute at the best available market rate'
        # STRATEGIC_EXECUTION = 'strategic_execution', 'Strategic Execution'
        BESTX = 'bestx', 'BestX - execute when Pangea expects optimal market conditions'

    settle_account_id = serializers.CharField(required=False, allow_null=True, default=None, help_text="Client-provided funding identifier. Will use default if configured. Otherwise, post-funded.")
    beneficiary_id = serializers.CharField(required=False, allow_null=True, default=None, help_text="Client-provided beneficiary identifier.")
    transaction_id = serializers.CharField(required=False, allow_null=True, default=None, help_text="Client-provided unique identifier for the transaction.")
    execution_strategy = serializers.ChoiceField(choices=ExecuteExecutionStrategies.choices, default=ExecuteExecutionStrategies.MARKET)

    open_date = serializers.DateField(required=False, help_text='Open date to indicate window forward')
    
    # modify save or full_save, full_clean, etc. in order to
    # self.data -> self.validated_data
    # to_internal: what the data is
    # to_representation: what data is post-validation

    def validate(self, attrs):
        # Add Validation logic here
        # check that to_ccy + from_ccy is valid
        # set market_name
        # check that ticket_type + action is valid

        basic = True if hasattr(self, 'basic_validation') else False
        attrs = shared_ticket_validation( attrs, basic=basic )

        return attrs

    def save(self):

        valid = self.validated_data

        # initialize states
        valid['internal_state'] = INTERNAL_STATES.DRAFT if valid.get('draft',None) else INTERNAL_STATES.NEW
        valid['external_state'] = EXTERNAL_STATES.PENDING
        valid['phase'] = PHASES.PRETRADE

        existing_ticket = None
        try:
            existing_ticket = Ticket.objects.get(cashflow_id=valid['cashflow_id'])
        except Ticket.DoesNotExist as e:
            pass
        except KeyError:
            pass

        # existing ticket with cashflow_id X exist, modify that ticket instead
        if existing_ticket:
            raise ValueError # this should never happen it is not valid and not proper
            for key in valid.keys():
                setattr(existing_ticket, key, valid[key])
            existing_ticket.save()
            ticket = existing_ticket
            self.instance = ticket
        else:
            ticket = super().save()

        topic = f'api2oms_{settings.APP_ENVIRONMENT}'
        ticket_data = ticket.export()
        logger.info( f'creating execute ticket: {ticket_data}')

        resp = enqueue(topic, ticket_data, uid=ticket.id, action=OMS_API_ACTIONS.CREATE, source='DJANGO_APP')
        logger.error(f'ENQUEUED: {topic} {type(resp)} {resp}')
        ticket.dispatch_event( WEBHOOK_EVENTS.TICKET_CREATED )
        return ticket

    class Meta:
        model = Ticket
        # These are the fields we want to expose publicly via the API
        fields = [
            'sell_currency',
            'buy_currency',
            'lock_side',
            'amount',
            'value_date',
            "tenor",
            'execution_strategy',
            'settle_account_id',
            'beneficiary_id',
            'beneficiaries',
            'customer_id',
            'cashflow_id',
            'transaction_id',
            'transaction_group',
            'date_conversion',
            'draft',
            'with_care',
            'payment_memo',
            'time_in_force',
            'ticket_type',
            'action',
            'destination',
            'broker',
            'start_time',
            'end_time',
            'trigger_time',
            'upper_trigger',
            'lower_trigger',
            'limit_trigger',
            'stop_trigger',
            'trader',
            'company',
            'auth_user',
            'market_name',
            'side',
            'settlement_info',
            'open_date',
        ]

# =======

class ExecuteGetSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField(format='hex_verbose', allow_null=False)

class ExecuteResponseSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField(format='hex_verbose')
    external_quote = serializers.FloatField()
    external_quote_expiry = serializers.DateTimeField()
    value_date = serializers.DateField()


