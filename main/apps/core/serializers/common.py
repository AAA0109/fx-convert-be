from hdlib.DateTime.Date import Date
from rest_framework import serializers


class HDLDateField(serializers.Field):
    def to_representation(self, value):
        return value.strftime("%Y-%m-%d")

    def to_internal_value(self, data):
        return Date.from_str(date=data, fmt="%Y-%m-%d")
