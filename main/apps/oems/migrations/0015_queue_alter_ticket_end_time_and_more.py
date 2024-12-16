# Generated by Django 4.2.10 on 2024-02-21 15:50

import django.core.validators
from django.db import migrations, models
import main.apps.oems.backend.utils
import main.apps.oems.models.extensions
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0014_ticket_eid'),
    ]

    operations = [
        migrations.CreateModel(
            name='Queue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('eid', models.UUIDField(default=uuid.uuid4)),
                ('enqueued_at', main.apps.oems.models.extensions.DateTimeWithoutTZField(auto_now_add=True)),
                ('dequeued_at', main.apps.oems.models.extensions.DateTimeWithoutTZField(blank=True, null=True)),
                ('action', models.TextField(blank=True, null=True)),
                ('topic', models.TextField(blank=True, validators=[django.core.validators.MinLengthValidator(1, 'the field must not be empty')])),
                ('uid', models.BigIntegerField(blank=True, null=True)),
                ('data', models.JSONField(blank=True, encoder=main.apps.oems.backend.utils.DateTimeEncoder)),
                ('resp', models.JSONField(blank=True, encoder=main.apps.oems.backend.utils.DateTimeEncoder, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='ticket',
            name='end_time',
            field=main.apps.oems.models.extensions.DateTimeWithoutTZField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='external_quote_expiry',
            field=main.apps.oems.models.extensions.DateTimeWithoutTZField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='external_state_start',
            field=main.apps.oems.models.extensions.DateTimeWithoutTZField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='internal_quote_expiry',
            field=main.apps.oems.models.extensions.DateTimeWithoutTZField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='internal_state_start',
            field=main.apps.oems.models.extensions.DateTimeWithoutTZField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='start_time',
            field=main.apps.oems.models.extensions.DateTimeWithoutTZField(blank=True, null=True),
        ),
    ]
