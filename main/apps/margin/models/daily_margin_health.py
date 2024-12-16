from typing import Iterable, Optional

from django.db import models
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import Company


class DailyMarginDetail(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)
    worst_margin_health = models.FloatField(null=False)
    best_margin_health = models.FloatField(null=False)

    @staticmethod
    def get_company_margin_healths(company: Company, start_date, end_date) -> Iterable['MarginDetail']:
        """ Get the company's daily margin details between the given dates ordered by created descending"""
        return DailyMarginDetail.objects.filter(company=company,
                                                created__gte=start_date,
                                                created__lt=end_date).order_by('-created')

    @staticmethod
    def insert_company_margin_health(company: Company, worst_margin_health: float, best_margin_health: float):
        DailyMarginDetail.objects.create(company=company,
                                         worst_margin_health=worst_margin_health,
                                         best_margin_health=best_margin_health)
