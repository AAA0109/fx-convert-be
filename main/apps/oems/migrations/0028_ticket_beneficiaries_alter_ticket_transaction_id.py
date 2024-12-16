# Generated by Django 4.2.10 on 2024-02-26 16:09

from django.db import migrations, models
import main.apps.oems.backend.utils


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0027_alter_ticket_limit_trigger_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='beneficiaries',
            field=models.JSONField(blank=True, encoder=main.apps.oems.backend.utils.DateTimeEncoder, null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='transaction_id',
            field=models.CharField(editable=False, help_text='Unique identifier for the transaction. Must be provided by the client to ensure idempotency.', max_length=128),
        ),
    ]
