from django_extensions.db.models import TimeStampedModel


class SpotDealRequest(TimeStampedModel):

    class Meta:
        abstract = True
