import logging

from django.conf import settings
from django.db import models
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from main.apps.core.constants import CURRENCY_HELP_TEXT, LOCK_SIDE_HELP_TEXT, VALUE_DATE_HELP_TEXT
from main.apps.currency.models import Currency
from main.apps.oems.api.serializers.fields import ValueDateField
from main.apps.oems.backend.states import INTERNAL_STATES, EXTERNAL_STATES, PHASES, OMS_API_ACTIONS
from main.apps.oems.backend.webhook import WEBHOOK_EVENTS
from main.apps.oems.backend.xover import enqueue
from main.apps.oems.models import Ticket
from main.apps.oems.validators.ticket import shared_ticket_validation

logger = logging.getLogger(__name__)


@extend_schema_serializer(
    exclude_fields=['trader', 'company', 'ticket_type', 'tenor', 'date_conversion', 'destination', 'draft','time_in_force',
                    'with_care', 'broker', 'market_name', 'side', 'beneficiaries', 'settlement_info','upper_trigger','lower_trigger',
                    'start_time','end_time','trigger_time','limit_trigger','stop_trigger','open_date'])
class RfqSerializer(serializers.ModelSerializer):
    class RfqExecutionStrategies(models.TextChoices):
        MARKET = 'market', 'Market'
        STRATEGIC_EXECUTION = 'strategic_execution', 'Strategic Execution'
        BESTX = 'bestx', 'Best Execution'

    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text=CURRENCY_HELP_TEXT)

    amount = serializers.FloatField(default=None, min_value=0.01,
                                    help_text='The amount of lock_side currency')  # TODO: min amount is dynamic

    lock_side = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                             help_text=LOCK_SIDE_HELP_TEXT)

    value_date = ValueDateField(required=True, help_text=VALUE_DATE_HELP_TEXT)

    class RfqTicketTypes(models.TextChoices):
        PAYMENT = 'payment', 'Payment'
        HEDGE = 'hedge', 'Hedge'

    ticket_type = serializers.ChoiceField(choices=RfqTicketTypes.choices, default=RfqTicketTypes.PAYMENT)

    class RfqTenor(models.TextChoices):
        SPOT = 'spot', 'Spot'
        FWD = 'fwd', 'Fwd'

    tenor = serializers.ChoiceField(choices=RfqTenor.choices, allow_null=True, required=False, default=None)
    date_conversion = serializers.ChoiceField(choices=Ticket.DateConvs.choices, default=Ticket.DateConvs.MODF)

    class RfqTimeInForces(models.TextChoices):
        _10SEC = '10sec', '10s'
        _1MIN = '1min', '1min'
        _1HR = '1hr', '1hr'

    class RfqExecutionStrategies(models.TextChoices):
        MARKET = 'market', 'Market - execute at the best available market rate'
        # STRATEGIC_EXECUTION = 'strategic_execution', 'Strategic Execution'
        BESTX = 'bestx', 'BestX - execute when Pangea expects optimal market conditions'

    time_in_force = serializers.ChoiceField(choices=RfqTimeInForces.choices, default=RfqTimeInForces._10SEC)
    settle_account_id = serializers.CharField(required=False, allow_null=True, default=None, help_text="Client-provided funding identifier. Will use default if configured. Otherwise, post-funded.")
    beneficiary_id = serializers.CharField(required=False, allow_null=True, default=None, help_text="Client-provided beneficiary identifier.")
    transaction_id = serializers.CharField(required=False, allow_null=True, default=None,
                                           help_text="Client-provided unique identifier for the transaction.")
    execution_strategy = serializers.ChoiceField(choices=RfqExecutionStrategies.choices, default=RfqExecutionStrategies.MARKET)

    # read only fields
    action = serializers.HiddenField(default='rfq')

    # draft = serializers.HiddenField(default=False)
    # with_care = serializers.HiddenField(default=False)
    # destination = serializers.HiddenField(default=None)
    # broker = serializers.HiddenField(default=None)

    ticket_id = serializers.UUIDField(format='hex_verbose', required=False,
                                      help_text='If you provide an existing ticket_id, the API will try to refresh your quote. If the ticket_id does not exist, using this parameter will result in an error.')

    # modify save or full_save, full_clean, etc. in order to
    # self.data -> self.validated_data
    # to_internal: what the data is
    # to_representation: what data is post-validation

    open_date = serializers.DateField(required=False, help_text='Open date to indicate window forward')

    def validate(self, attrs):

        attrs = shared_ticket_validation(attrs)

        # TODO:
        # if you are a spot transaction going to corpay for this FxPair and client is eligible for mass payments,
        # validate the beneficiary object... that all the necessary fields are filled out.
        # do not indicate to the customer in any way that this is corpay specific. even if we collect information
        # that corpay doesn't need or use.
        # set up routing to destination accordingly

        # check that to_ccy + from_ccy is valid
        # set market_name
        # check that ticket_type + action is valid

        return attrs

    def save(self):
        from main.apps.oems.backend.rfq_utils import do_api_rfq, do_indicative_rfq
        valid = self.validated_data

        # initialize states
        valid['internal_state'] = INTERNAL_STATES.DRAFT if valid.get('draft', None) else INTERNAL_STATES.NEW
        valid['external_state'] = EXTERNAL_STATES.PENDING
        valid['phase'] = PHASES.PRETRADE

        ticket = super().save()

        rfq_type = ticket.rfq_type

        if rfq_type == Ticket.RfqType.API:
            # TODO: check if client is eligible for mass payments. route accordingly.
            if do_api_rfq(ticket):
                ticket.save()
        elif rfq_type == Ticket.RfqType.INDICATIVE:
            if do_indicative_rfq(ticket):
                ticket.save()
        elif rfq_type == Ticket.RfqType.NORFQ or rfq_type == Ticket.RfqType.UNSUPPORTED:
            raise serializers.ValidationError("This market does not support RFQ.")

        logger.info( f'creating rfq ticket: {ticket.export()}')

        if ticket.internal_state != INTERNAL_STATES.RFQ_DONE and ticket.internal_state not in INTERNAL_STATES.OMS_TERMINAL_STATES:
            data = ticket.export()
            topic = f'api2oms_{settings.APP_ENVIRONMENT}'
            resp = enqueue(topic, data, uid=ticket.id, action=OMS_API_ACTIONS.CREATE,
                           source='DJANGO_APP')
            logger.error(f'ENQUEUED: {topic} {type(resp)} {resp}')

        ticket.dispatch_event(WEBHOOK_EVENTS.TICKET_CREATED)

        return ticket

    class Meta:
        model = Ticket
        # These are the fields we want to expose publicly via the API
        fields = [
            'sell_currency',
            'buy_currency',
            'lock_side',
            'ticket_type',
            'value_date',
            'tenor',
            'amount',
            'execution_strategy',
            'ticket_id',
            'settle_account_id',
            'beneficiary_id',
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
            'beneficiaries',
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
            'market_name',
            'side',
            'settlement_info',
            'open_date',
        ]


class RfqGetSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField(format='hex_verbose', allow_null=False)


class RfqResponseSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField(format='hex_verbose')
    external_quote = serializers.FloatField()
    external_quote_expiry = serializers.DateTimeField()
    value_date = serializers.DateField()


class RfqRefreshSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField(format='hex_verbose', default=None)
    transaction_id = serializers.CharField(max_length=255, min_length=1, allow_blank=True, default=None,
                                           help_text="Unique identifier for the transaction.")
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text='ISO 4217 Standard 3-Letter Currency Code', default=None)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                help_text='ISO 4217 Standard 3-Letter Currency Code', default=None)
    amount = serializers.FloatField(default=None, min_value=0.01)
    ticket_type = serializers.ChoiceField(choices=RfqSerializer.RfqTicketTypes.choices, default=None)
    tenor = serializers.ChoiceField(choices=RfqSerializer.RfqTenor.choices, default=None)
    time_in_force = serializers.ChoiceField(choices=RfqSerializer.RfqTimeInForces.choices, default=None)
