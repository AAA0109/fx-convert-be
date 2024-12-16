from django.db import models
from main.apps.currency.models.currency import Currency


class Country(models.Model):
    STRICT_GATE = 'strict_gate'
    SOFT_GATE = 'soft_gate'
    PERSUASIVE = 'persuasive'
    OPEN = 'open'

    STRICTNESS_CHOICES = [
        (STRICT_GATE, 'Strict Gate'),
        (SOFT_GATE, 'Soft Gate'),
        (PERSUASIVE, 'Persuasive'),
        (OPEN, 'Open'),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=4)
    use_in_average = models.BooleanField(null=False, default=False)
    use_in_explore = models.BooleanField(null=False, default=False)
    currency_code = models.ForeignKey(
        Currency, on_delete=models.CASCADE, to_field='mnemonic', related_name='countries', db_column='currency_code', null=True, blank=True)
    strictness_of_capital_controls = models.CharField(
        max_length=12,  # maximum length needed to store the longest choice
        choices=STRICTNESS_CHOICES,
        default=OPEN,
        verbose_name='Strictness of Capital Controls'
    )
    strictness_of_capital_controls_description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Description for Strictness of Capital Controls'
    )

    def __str__(self) -> str:
        return self.name.title()
