from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import Company, User


def file_uploaded_to(instance, filename: str):
    return 'corpay/{0}/onboarding'.format(instance.company.pk)


class Onboarding(TimeStampedModel):
    company = models.OneToOneField(Company, on_delete=models.CASCADE)
    client_onboarding_id = models.CharField(max_length=32)


class OnboardingFile(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=60)
    file = models.FileField(upload_to=file_uploaded_to)
    onboarding = models.ForeignKey(Onboarding, on_delete=models.CASCADE)

    class FileStatus(models.TextChoices):
        NEW = 'new', _('New')
        SENT_TO_CORPAY = 'send_to_corpay', _('Sent to Corpay')
        REVIEWED = 'reviewed', _('Reviewed')
        ERROR = 'error', _('Error')

    status = models.CharField(max_length=20, choices=FileStatus.choices, default=FileStatus.NEW, null=False,
                              blank=False)
