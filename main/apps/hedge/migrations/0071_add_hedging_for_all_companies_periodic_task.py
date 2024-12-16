# Generated by Django 4.2.11 on 2024-05-08 01:48

from django.db import migrations
from django.apps.registry import Apps


def add_hedging_all_companies_periodic_task(apps:Apps, schema_editor):
    import json
    from django_celery_beat.models import PeriodicTask, CrontabSchedule

    crontab_schedule, created = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='17',
        day_of_week='1,2,3,4,5',
        timezone='America/New_York'
    )

    task, created = PeriodicTask.objects.get_or_create(
        name="Hedging All Companies",
        defaults={
            'crontab': crontab_schedule,
            'task': 'main.apps.hedge.tasks.company_hedging.task_hedging_for_all_companies',
            'args': json.dumps([]),
            'kwargs': json.dumps({}),
            'enabled': False,
        }
    )


def remove_hedging_all_companies_periodic_task(apps:Apps, schema_editor):
    from django_celery_beat.models import PeriodicTask

    try:
        task = PeriodicTask.objects.get(name="Hedging All Companies")
        task.delete()
    except PeriodicTask.DoesNotExist:
        pass



class Migration(migrations.Migration):

    dependencies = [
        ('hedge', '0070_create_fwd_to_ticket_celery_task'),
    ]

    operations = [
        migrations.RunPython(add_hedging_all_companies_periodic_task, remove_hedging_all_companies_periodic_task)
    ]
