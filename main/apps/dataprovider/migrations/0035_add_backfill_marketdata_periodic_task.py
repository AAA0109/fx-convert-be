# Generated by Django 4.2.11 on 2024-05-13 16:54

from django.db import migrations
from django.apps.registry import Apps


def add_backfill_marketdata_periodic_task(apps:Apps, schema_editor):
    import json
    from django_celery_beat.models import PeriodicTask, IntervalSchedule

    schedule_01d, created = IntervalSchedule.objects.get_or_create(
        every=1,
        period=IntervalSchedule.DAYS,
    )

    task, created = PeriodicTask.objects.get_or_create(
        name='Backfill Market Data for Profile Ids',
        defaults={
            'interval': schedule_01d,
            'task': 'main.apps.dataprovider.tasks.backfill_marketdata_by_profile.backfill_marketdata_for_profile_ids',
            'args': json.dumps([]),
            'kwargs': json.dumps({}),
            'enabled': False,
        }
    )


def remove_backfill_marketdata_periodic_task(apps:Apps, schema_editor):
    from django_celery_beat.models import PeriodicTask

    try:
        task = PeriodicTask.objects.get(
            name='Backfill Market Data for Profile Ids',
            task='main.apps.dataprovider.tasks.backfill_marketdata_by_profile.backfill_marketdata_for_profile_ids')
        task.delete()
    except PeriodicTask.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('dataprovider', '0034_disable_ibkr_tws_source_importer_profile'),
    ]

    operations = [
        migrations.RunPython(add_backfill_marketdata_periodic_task, remove_backfill_marketdata_periodic_task)
    ]
