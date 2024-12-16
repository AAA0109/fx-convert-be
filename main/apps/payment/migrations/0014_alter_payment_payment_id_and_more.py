# Generated by Django 4.2.11 on 2024-05-23 20:21

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0013_auto_20240523_1956'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='payment_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_status',
            field=models.CharField(choices=[('awaiting_funds', 'Awaiting Funds'), ('booked', 'Booked'), ('delivered', 'Delivered'), ('drafting', 'Drafting'), ('in_transit', 'In Transit'), ('scheduled', 'Scheduled'), ('working', 'Working'), ('canceled', 'Canceled'), ('failed', 'Failed'), ('settlement_issue', 'Settlement Issue'), ('pend_auth', 'Pending Authorization')], default='drafting', max_length=25),
        ),
    ]