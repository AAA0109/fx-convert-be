# Generated by Django 4.2.11 on 2024-05-16 16:47

from django.db import migrations, models
import main.apps.oems.backend.utils


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0084_auto_20240515_0123'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='mass_payment_info',
            field=models.JSONField(blank=True, encoder=main.apps.oems.backend.utils.DateTimeEncoder, null=True),
        ),
    ]
