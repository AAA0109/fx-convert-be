from rest_framework import serializers

from main.apps.account.models import Company
from main.apps.oems.models import Ticket
from main.apps.currency.models import Currency
from main.apps.oems.validators.ticket import shared_ticket_validation
from main.apps.core.constants import CURRENCY_HELP_TEXT, LOCK_SIDE_HELP_TEXT

class TicketSerializer(serializers.ModelSerializer):

    company = serializers.PrimaryKeyRelatedField(allow_null=True, queryset=Company.objects.all())

    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(), help_text=CURRENCY_HELP_TEXT)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(), help_text=CURRENCY_HELP_TEXT)
    amount = serializers.FloatField(required=True, min_value=1.0)
    lock_side = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=LOCK_SIDE_HELP_TEXT)

    def validate(self, attrs):
        attrs = shared_ticket_validation( attrs )
        return attrs


    class Meta:
        model = Ticket
        # These are the fields we want to expose publicly via the API
        fields = [
            'ticket_id',
            'company',
            'customer_id',
            'sell_currency',
            'buy_currency',
            'amount',
            'lock_side',
            'tenor',
            'value_date',
            'draft',
            'time_in_force',
            'transaction_id',
            'transaction_group',
            'ticket_type',
            'action',
            'start_time',
            'end_time',
            'order_length',
            'execution_strategy',
            'broker',
            'algo',
            'algo_fields',
            'upper_trigger',
            'lower_trigger',
            'trader',
        ]
