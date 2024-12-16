from rest_framework import serializers


class PurposeOfPaymentRequestSerializer(serializers.Serializer):
    country = serializers.CharField()
    currency = serializers.CharField()
    PURPOSE_OF_PAYMENT_METHODS = (
        ('W', 'Wire'),
        ('E', 'iACH')
    )
    method = serializers.ChoiceField(choices=PURPOSE_OF_PAYMENT_METHODS)


class PurposeOfPaymentItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    text = serializers.CharField()
    search_text = serializers.CharField(source='searchText')


class PurposeOfPaymentResponseSerializer(serializers.Serializer):
    items = PurposeOfPaymentItemSerializer(many=True)
