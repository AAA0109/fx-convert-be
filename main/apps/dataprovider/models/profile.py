from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as __
from multiselectfield import MultiSelectField

from main.apps.marketdata.models import DataCut
from .source import Source


DAYS_CHOICES = (
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday')
)


class Profile(models.Model):
    class FileFormat(models.TextChoices):
        CSV = 'csv', __('csv')
        XML = 'xml', __('xml')
        FIXML = 'fixml', __('fixml')
        JSON = 'json', __('json')
        API = 'api', __('api'),
        HTML = 'html', __('html'),
        TXT = 'txt', __('txt'),
        XLSX = 'xlsx', __('xlsx')
        MODEL = 'model', __('model')
        ZIP = 'zip', __('zip')
        TAR_GZ = 'tar.gz', __('tar.gz')

    name = models.CharField(max_length=255)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    url = models.CharField(max_length=255, null=True, blank=True)
    filename = models.CharField(max_length=255, help_text='Supports regex pattern', null=True, blank=True)
    directory = models.CharField(max_length=255, default='/', null=True, blank=True)
    file_format = models.CharField(max_length=10, choices=FileFormat.choices, default=FileFormat.CSV)
    enabled = models.BooleanField(default=False)
    target = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    data_cut_type = models.IntegerField(choices=DataCut.CutType.choices, default=DataCut.CutType.EOD, null=False,
                                        blank=True)
    days = MultiSelectField(choices=DAYS_CHOICES, help_text="Days to import data on", default=[0, 1, 2, 3, 4])
    options = models.JSONField(default=defaultdict, help_text="Profile options", blank=True, null=True)
    extract_for_profile_ids = models.CharField(null=True, blank=True,
                                               help_text="Profile ids related to the downloaded archived file")

    def __str__(self):
        return f"{self.name} | {self.source.name}"

    class Meta:
        verbose_name_plural = "  Profiles"


class ProfileParallelOption(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    field = models.CharField(max_length=32)

    class Type(models.TextChoices):
        MANUAL = "manual", __("Manual")
        DYNAMIC = "dynamic", __("Dynamic")

    type = models.CharField(choices=Type.choices, default=Type.MANUAL)

    class Provider(models.TextChoices):
        FXPAIR = "fxpair", __("FX Pair")
        COMPANY = "company", __("Company")

    provider = models.CharField(choices=Provider.choices, default=None, null=True, blank=True)

    class Instrument(models.TextChoices):
        SPOT = "spot", __("Spot")
        FORWARD = "forward", __("Forward")

    instrument = models.CharField(choices=Instrument.choices, default=None, null=True, blank=True)

    ids = models.TextField(null=True, blank=True)

    def generate_dynamic_ids(self):
        from ..services.profile.factories.id import ParallelIdGeneratorFactory
        factory = ParallelIdGeneratorFactory()
        return factory.generate_dynamic_ids(self)
