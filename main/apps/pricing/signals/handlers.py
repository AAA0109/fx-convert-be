from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from main.apps.pricing.models import Feed


@receiver(pre_save, sender=Feed)
def update_feed_tag(sender, instance, **kwargs):
    try:
        channel_group_str = instance.channel_group if instance.channel_group else ""
        tick_type_str = instance.tick_type if instance.tick_type else ""
        feed_type_str = instance.feed_type if instance.feed_type else ""
        collector_name_str = instance.collector_name if instance.collector_name else ""

        instance.tag = f"{instance.feed_name},{channel_group_str},{tick_type_str},{feed_type_str},{collector_name_str}"
    except Exception as e:
        raise ValidationError(_("Error updating tag: %(error)s"), params={'error': str(e)})
