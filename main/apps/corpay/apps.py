from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CorpayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main.apps.corpay'

    def ready(self) -> None:
        # Importing models here to avoid app registry and models not ready error
        from django_celery_beat.models import PeriodicTask, IntervalSchedule
        from django.dispatch import receiver
        import json

        # Use the post_migrate signal to ensure this code runs after the database is ready
        @receiver(post_migrate, sender=self)
        def create_periodic_tasks(sender, **kwargs):
            schedule_01d, created = IntervalSchedule.objects.update_or_create(
                every=1,
                period=IntervalSchedule.DAYS,
            )

            task, created = PeriodicTask.objects.get_or_create(
                name="Clean corpay ApiRequestLog",
                defaults={
                    'interval': schedule_01d,
                    'task': 'main.apps.core.tasks.clean_a_table_in_database.clean_a_table_in_database',
                    'args': json.dumps(['corpay', 'ApiRequestLog', 7]),
                    'kwargs': json.dumps({}),
                    'enabled': False,
                }
            )

            task, created = PeriodicTask.objects.get_or_create(
                name="Clean corpay ApiResponseLog",
                defaults={
                    'interval': schedule_01d,
                    'task': 'main.apps.core.tasks.clean_a_table_in_database.clean_a_table_in_database',
                    'args': json.dumps(['corpay', 'ApiResponseLog', 7]),
                    'kwargs': json.dumps({}),
                    'enabled': False,
                }
            )
