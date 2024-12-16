from rest_framework import serializers

from main.apps.oems.models import ManualRequest


class ManualRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManualRequest
        fields = '__all__'
