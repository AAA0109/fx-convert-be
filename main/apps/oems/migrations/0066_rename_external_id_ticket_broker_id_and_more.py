# Generated by Django 4.2.11 on 2024-04-17 21:55

from django.db import migrations, models
import main.apps.oems.models.extensions


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0065_ticket_fixing_source'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ticket',
            old_name='external_id',
            new_name='broker_id',
        ),
        migrations.AddField(
            model_name='ticket',
            name='broker_state',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ticket',
            name='broker_state_start',
            field=main.apps.oems.models.extensions.DateTimeWithoutTZField(blank=True, null=True),
        ),
    ]