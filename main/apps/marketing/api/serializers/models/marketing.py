from rest_framework import serializers

class FxCalculatorSerializer(serializers.Serializer):
    targetCurrency = serializers.CharField()
    sourceCurrency = serializers.CharField()
    sourceAmount = serializers.FloatField()


class FxCalculatorResponseSerializer(serializers.Serializer):
    targetAmount = serializers.DecimalField(max_digits=15, decimal_places=2)

class DemoFormRequestSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    company = serializers.CharField()
    company_url = serializers.CharField()
    jobtitle = serializers.CharField()
    friend_referral = serializers.CharField()
    do_you_have_employees_living_working_internationally_ = serializers.CharField()
    annual_international_transaction_volume = serializers.CharField()
    currencies = serializers.CharField()

class DemoResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    contact_id = serializers.CharField()
    company_id = serializers.CharField()
