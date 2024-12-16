from django.db import models

from main.apps.account.models.company import Company


class CompanyLimitSetting(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, null=False,
                                   related_name='limit_setting')

    # Company's max spot sell transaction amount
    max_amount_sell_spot = models.DecimalField(max_digits=20, decimal_places=2, default=0.0,
                                               help_text='Maximum spot transaction sell amount',
                                               verbose_name='Spot Max Sell Amount')

    # Company's max spot buy transaction amount
    max_amount_buy_spot = models.DecimalField(max_digits=20, decimal_places=2, default=0.0,
                                               help_text='Maximum spot transaction buy amount',
                                               verbose_name='Spot Max Buy Amount')

    # Company's max forward sell transaction amount
    max_amount_sell_fwd = models.DecimalField(max_digits=20, decimal_places=2, default=0.0,
                                               help_text='Maximum forward transaction sell amount',
                                               verbose_name='Forward Max Sell Amount')

    # Company's max forward buy transaction amount
    max_amount_buy_fwd = models.DecimalField(max_digits=20, decimal_places=2, default=0.0,
                                               help_text='Maximum forward transaction buy amount',
                                               verbose_name='Forward Max Buy Amount')

    # Company's max forward transaction tenor in month
    max_tenor_in_month = models.IntegerField(verbose_name='Maximum Tenor in Month',
                                             help_text='Maximum forward transaction tenor in month',
                                             null=True)
