from django.db import models
from django.utils.translation import gettext_lazy as __

from .dataprovider import DataProvider


class Source(models.Model):
    class DataType(models.TextChoices):
        LOCAL_STORAGE = 'local_storage', __('Local Storage'),
        SFTP = 'sftp', __('SFTP'),
        REST_API = 'rest', __('REST API'),
        GCP = 'gcp', __('Google Cloud'),
        IBKR_TWS = 'ibkr_tws', __('IBKR TWS'),
        IBKR_WEB = 'ibkr_web', __('IBKR Web')
        CORPAY_API = 'corpay', __('CorPay API')
        MODEL = 'model', __('Model')

    data_type = models.CharField(max_length=255, choices=DataType.choices, default=DataType.LOCAL_STORAGE)
    sftp_host = models.CharField(max_length=255, null=True, blank=True, verbose_name=__('SFTP Host'))
    sftp_port = models.IntegerField(null=True, blank=True, verbose_name=__('SFTP Port'))
    sftp_username = models.CharField(max_length=255, null=True, blank=True, verbose_name=__('SFTP Username'))
    sftp_password = models.CharField(max_length=255, null=True, blank=True, verbose_name=__('SFTP Password'))
    sftp_dir = models.CharField(max_length=255, null=True, blank=True, verbose_name=__('SFTP Directory'))

    data_provider = models.ForeignKey(DataProvider, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "   Sources"
