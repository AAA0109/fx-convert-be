from django.db import models

from hdlib.DateTime.Date import Date

from main.apps.util import get_or_none

from typing import Optional


class DataCut(models.Model):
    cut_time = models.DateTimeField(unique=True, null=False)
    ordering = ['-cut_time']

    class CutType(models.IntegerChoices):
        EOD = 1  # End of day cut
        INTRA = 2  # Intraday data at regular interval
        BENCHMARK = 3  # Benchmark rate

    cut_type = models.IntegerField(null=False, choices=CutType.choices)

    def __str__(self):
        return f"{self.pk} - {self.cut_type} - {self.cut_time}"
    @staticmethod
    @get_or_none
    def get_exact_cut(date: Date) -> Optional[Date]:
        return DataCut.objects.get(cut_time=date)

    @property
    def date(self) -> Date:
        return Date.from_datetime_date(self.cut_time.date())

    @staticmethod
    def create_cut(time: Date, cut_type: CutType) -> 'DataCut':
        return DataCut.objects.create(cut_time=time, cut_type=cut_type)


class MarketData(models.Model):
    # The date for this market data, note that this is also contained in the data_cut
    date = models.DateTimeField()

    # The data cut this market data comes from.
    data_cut = models.ForeignKey(DataCut, on_delete=models.CASCADE, null=False)

    class Meta:
        abstract = True

    @property
    def data_time(self):
        """ A function to get the time that the data comes from. """
        return self.data_cut.cut_time
