from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from timezone_field.choices import standard, with_gmt_offset
from timezone_field.backends import get_tz_backend, TimeZoneNotFoundError


class TimeZoneSerializerChoiceField(serializers.ChoiceField):
    default_error_messages = {
        "invalid": _("A valid timezone is required."),
    }

    def __init__(self, *args, **kwargs):
        self.use_pytz = kwargs.pop("use_pytz", None)
        self.tz_backend = get_tz_backend(use_pytz=self.use_pytz)
        self.default_tzs = [self.tz_backend.to_tzobj(v) for v in self.tz_backend.base_tzstrs]

        kwargs["choices"] = [tz.zone for tz in self.default_tzs]

        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        data_str = force_str(data)
        try:
            return self.tz_backend.to_tzobj(data_str)
        except TimeZoneNotFoundError:
            self.fail("invalid")

    def to_representation(self, value):
        return str(value)
