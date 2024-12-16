from rest_framework import serializers
from datetime import datetime, date

class ValueDateField(serializers.Field):

	# Validate and convert input data
	allowed_strings = {"SPOT", "RTP", "EOD", "TOM", "EOM"}

	def to_internal_value(self, data):
		
		# If data is one of the allowed strings, return it directly
		if data in self.allowed_strings:
			return data
		
		# Try to parse the data as a date
		if isinstance(data, datetime):
			return data.date()
		elif isinstance(data, date):
			return data

		try:
			return datetime.strptime(data, '%Y-%m-%d').date()
		except ValueError:
			try:
				return datetime.fromisoformat(data).date() # strptime(data, '%Y-%m-%dT%H:%M:%S').date()
			except ValueError:
				raise serializers.ValidationError("This field must be a valid date or one of the following strings: SPOT, RTP, EOD, TOM, EOM.")
	
	def to_representation(self, value):
		# Convert Python objects to a datatype serializable by JSON
		if isinstance(value, date):
			return value.isoformat()
		elif isinstance(value, str):
			return value
		else:
			raise Exception('Unexpected type')


class CurrencyAmountField(serializers.DecimalField):
    def __init__(self, *args, **kwargs):
        # Provide default values for max_digits and decimal_places
        kwargs['max_digits'] = 19
        kwargs['decimal_places'] = 4
        super().__init__(*args, **kwargs)

class CurrencyRateField(serializers.DecimalField):
    def __init__(self, *args, **kwargs):
        # Provide default values for max_digits and decimal_places
        kwargs['max_digits'] = 19
        kwargs['decimal_places'] = 9
        super().__init__(*args, **kwargs)

class InternalDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, data):
        if isinstance(data, datetime):
            return data
        return super().to_internal_value(data)

class InternalDateField(serializers.DateField):
    def to_internal_value(self, data):
        if isinstance(data, date):
            return data
        return super().to_internal_value(data)

