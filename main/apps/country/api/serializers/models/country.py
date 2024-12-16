from rest_framework import serializers
from main.apps.country.models import Country


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = (
            "name",
            "code",
            "currency_code",
            "use_in_average",
            "use_in_explore",
            "strictness_of_capital_controls",
            "strictness_of_capital_controls_description"
        )
