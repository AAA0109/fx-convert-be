from django.db.models import DateTimeField, DecimalField

class DateTimeWithoutTZField(DateTimeField):
    def db_type(self, connection):
        return 'timestamp'
        
class CurrentTimestampField(DateTimeField):
    def db_type(self, connection):
        return 'timestamp default current_timestamp'

class CurrencyAmountField(DecimalField):
    def __init__(self, *args, **kwargs):
        # Set default values for max_digits and decimal_places
        kwargs['max_digits'] = 19
        kwargs['decimal_places'] = 4
        super().__init__(*args, **kwargs)

class CurrencyRateField(DecimalField):
    def __init__(self, *args, **kwargs):
        # Set default values for max_digits and decimal_places
        kwargs['max_digits'] = 19
        kwargs['decimal_places'] = 9
        super().__init__(*args, **kwargs)
