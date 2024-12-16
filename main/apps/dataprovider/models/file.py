from django.db import models
from django.utils.translation import gettext_lazy as __
from .dataprovider import DataProvider
from .profile import Profile
from .source import Source


def file_uploaded_to(instance, filename: str):
    return 'data_store/{0}'.format(instance.file_path)


class File(models.Model):
    class FileStatus(models.IntegerChoices):
        QUEUED = 0, __('Queued')
        DOWNLOADED = 1, __('Downloaded')
        PREPROCESSING = 2, __('Preprocessing')
        PREPROCESSED = 3, __('Preprocessed')
        ERROR = 4, __('Error')

    data_provider = models.ForeignKey(DataProvider, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255)
    file = models.FileField(upload_to=file_uploaded_to, default=None, null=True, blank=True)
    status = models.IntegerField(choices=FileStatus.choices, default=None, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
