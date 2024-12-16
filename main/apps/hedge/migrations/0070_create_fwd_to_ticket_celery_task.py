# Generated by Django 4.2.10 on 2024-03-25 16:51

import json

from django.apps.registry import Apps
from django.db import migrations

def create_fwd_to_ticket_celery_task(apps: Apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    # Convert Autopilot Forward to Ticket
    task, created = PeriodicTask.objects.get_or_create(
        name='Convert Autopilot Forward to Ticket',  # Human-readable name of the task
        defaults={
            'interval': None,
            'task': 'main.apps.hedge.tasks.convert_forward_to_ticket.convert_forward_to_ticket_with_strategy',
            'args': json.dumps([]),
            'kwargs': json.dumps({}),
            'enabled': False,
        }
    )

def remove_fwd_to_ticket_celery_task(apps: Apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    try:
        task = PeriodicTask.objects.get(
            name='Convert Autopilot Forward to Ticket',
            task='main.apps.hedge.tasks.convert_forward_to_ticket.convert_forward_to_ticket_with_strategy'
        )
        task.delete()
    except Exception as e:
        print(f"{e}")
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('hedge', '0069_merge_20240308_1439'),
    ]

    operations = [
        migrations.RunPython(create_fwd_to_ticket_celery_task, remove_fwd_to_ticket_celery_task)
    ]
