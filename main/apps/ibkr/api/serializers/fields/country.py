from django_countries.serializer_fields import CountryField
from django.utils.encoding import force_str


class IBCountryField(CountryField):
    def to_internal_value(self, data):
        if not self.allow_blank and data == "":
            self.fail("invalid_choice", input=data)

        if isinstance(data, dict):
            data = data.get("code")
        country = self.countries.alpha3(data)
        if data and not country:
            country = self.countries.by_name(force_str(data))
            if not country:
                self.fail("invalid_choice", input=data)
        return country
