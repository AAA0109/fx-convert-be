from rest_framework import serializers

from main.apps.broker.models import BrokerAccount, Broker


class BrokerAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerAccount
        fields = '__all__'


class BrokerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Broker
        fields = (
            'id',
            'name',
            'broker_provider'
        )
