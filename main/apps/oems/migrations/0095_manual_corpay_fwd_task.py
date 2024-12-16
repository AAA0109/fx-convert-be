# Generated by Django 4.2.10 on 2024-03-25 16:51

import json

from django.apps.registry import Apps
from django.db import migrations
from django_celery_beat.models import PeriodicTask, IntervalSchedule

def create_fwd_to_ticket_celery_task(apps: Apps, schema_editor):
    # PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    schedule, created = IntervalSchedule.objects.get_or_create(
        every=2,
        period=IntervalSchedule.HOURS,
    )

    # Convert Autopilot Forward to Ticket
    task, created = PeriodicTask.objects.get_or_create(
        name='Sync Corpay Manual Forward Trading',  # Human-readable name of the task
        defaults={
            'interval': schedule,
            'task': 'main.apps.oems.tasks.corpay_manual_fwds.task_check_corpay_manual_fwds',
            'args': json.dumps([]),
            'kwargs': json.dumps({}),
            'enabled': False,
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0094_manualrequest_broker_id_manualrequest_fwd_points_and_more'),
    ]

    operations = [
        migrations.RunPython(create_fwd_to_ticket_celery_task)
    ]
