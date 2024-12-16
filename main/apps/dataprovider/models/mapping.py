from django.db import models

from .dataprovider import DataProvider
from .profile import Profile


class Mapping(models.Model):
    data_provider = models.ForeignKey(DataProvider, on_delete=models.CASCADE, null=True, blank=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True)
    column_name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.column_name

    class Meta:
        verbose_name_plural = " Mappings"
