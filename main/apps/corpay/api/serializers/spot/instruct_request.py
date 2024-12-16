from rest_framework import serializers
from main.apps.corpay.models.spot.instruct_request import InstructRequest


class SaveInstructRequestResponseSerializer(serializers.ModelSerializer):

    class Meta:
        model = InstructRequest
        fields = '__all__'
