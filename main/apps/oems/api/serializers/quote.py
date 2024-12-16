from rest_framework import serializers

from main.apps.oems.models import Quote


class QuoteRequestSerializer(serializers.Serializer):
    from_currency = serializers.CharField()
    to_currency = serializers.CharField()


class CreateQuoteRequestSerializer(QuoteRequestSerializer):\
    pass


class UpdateQuoteRequestSerializer(QuoteRequestSerializer):
    order_id = serializers.IntegerField()


class QuoteResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = '__all__'


class QuoteToOrderRequestSerializer(serializers.Serializer):
    quote_id = serializers.IntegerField()
    wait_condition_id = serializers.IntegerField(required=False)
    payment_id = serializers.IntegerField(required=False)
    cashflow_id = serializers.IntegerField(required=False)


class QuoteToTicketRequestSerializer(QuoteToOrderRequestSerializer):
    pass
