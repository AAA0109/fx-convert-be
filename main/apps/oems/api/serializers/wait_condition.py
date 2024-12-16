from rest_framework import serializers

from main.apps.oems.models import WaitCondition


class WaitConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitCondition
        fields = '__all__'
