# Generated by Django 3.2.8 on 2022-08-11 23:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from main.apps.notification.models import NotificationEvent


def init_notification_events(apps, schema_editor):
    events = [
        NotificationEvent(name='Margin low', key='margin-low', type=NotificationEvent.EventType.MARGIN),
        NotificationEvent(name='Margin call', key='margin-call', type=NotificationEvent.EventType.MARGIN),
        NotificationEvent(name='Margin deposited', key='margin-deposited',
                          type=NotificationEvent.EventType.MARGIN),
        NotificationEvent(name='Margin received', key='margin-received',
                          type=NotificationEvent.EventType.MARGIN),
        NotificationEvent(name='A hedge becomes active', key='hedge-active',
                          type=NotificationEvent.EventType.HEDGE),
        NotificationEvent(name='A hedge is about to settle', key='hedge-settling',
                          type=NotificationEvent.EventType.HEDGE),
        NotificationEvent(name='A hedge becomes unhealthy', key='hedge-unhealthy',
                          type=NotificationEvent.EventType.HEDGE),
    ]

    NotificationEvent.objects.bulk_create(events)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('key', models.CharField(max_length=255)),
                ('type', models.IntegerField(choices=[(1, 'Margin'), (2, 'Hedge')])),
            ],
        ),
        migrations.CreateModel(
            name='UserNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.BooleanField(default=False)),
                ('sms', models.BooleanField(default=False)),
                ('phone', models.BooleanField(default=False)),
                ('event',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='notification.notificationevent')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(init_notification_events)
    ]
