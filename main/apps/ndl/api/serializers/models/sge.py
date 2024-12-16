from rest_framework import serializers
from main.apps.ndl.models.sge import sge


class SGESerializer(serializers.ModelSerializer):

    class Meta:
        model = sge
        fields = (
            "date",
            "value_type",
            "value",
            "currency_id",
            "country_codes"
        )
