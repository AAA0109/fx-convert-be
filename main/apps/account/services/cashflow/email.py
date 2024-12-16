from abc import ABC

from dateutil.rrule import rrulestr
from django.conf import settings
from django.utils import formats

from main.apps.account.models import CashFlow
from main.apps.currency.models.currency import Currency
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider


class CashflowEmailService(ABC):

    @staticmethod
    def get_payment_type(cashflow: CashFlow):
        if cashflow.installment_id:
            return "Installment"
        if cashflow.periodicity is not None:
            return "Recurring"
        return "One-time"

    @staticmethod
    def convert_currency_rate(currency: Currency, amount: float):
        return FxSpotProvider().convert_currency_rate(currency, Currency.get_currency(currency='USD'), amount)

    @staticmethod
    def get_payment_date(cashflow: CashFlow):
        if cashflow.periodicity is None:
            return formats.date_format(cashflow.date, settings.SHORT_DATE_FORMAT)
        else:
            return CashflowEmailService.human_readable_rrule(cashflow.periodicity)

    @staticmethod
    def human_readable_rrule(rrule_string):
        rule = rrulestr(rrule_string)

        if rule._freq == 0:
            result = 'Every second'
        elif rule._freq == 1:
            result = 'Every minute'
        elif rule._freq == 2:
            result = 'Every hour'
        elif rule._freq == 3:
            if rule._interval == 2:
                result = 'Every other day'
            else:
                result = 'Daily'
        elif rule._freq == 4:
            if rule._interval == 2:
                result = 'Every other week on '
            else:
                result = 'Every week on '
            if rule._byweekday:
                weekdays = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']
                human_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                result += ', '.join(human_days[weekdays.index(day)] for day in rule._byweekday)
        elif rule._freq == 5:
            if rule._interval == 2:
                result = 'Every other month on the '
            else:
                result = 'Every month on the '
            if rule._bymonthday:
                result += ', '.join(str(day) for day in rule._bymonthday)
            result += 'th'
        elif rule._freq == 6:
            if rule._interval == 2:
                result = 'Every other year on '
            else:
                result = 'Every year on '
            if rule._bymonth and rule._bymonthday:
                months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
                          'October', 'November', 'December']
                result += months[rule._bymonth[0] - 1] + ' ' + str(rule._bymonthday[0])
        else:
            return 'Invalid rrule string'

        if rule._interval > 2:
            result += f', every {rule._interval} periods'

        if rule._dtstart:
            result += f' from {rule._dtstart.strftime("%B %d, %Y")}'

        if rule._until:
            result += f' to {rule._until.strftime("%B %d, %Y")}'
        elif rule._count:
            result += f', for {rule._count} times'

        return result
