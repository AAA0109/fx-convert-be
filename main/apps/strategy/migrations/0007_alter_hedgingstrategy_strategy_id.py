# Generated by Django 4.2.10 on 2024-03-05 00:49

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('strategy', '0006_remove_autopilothedgingstrategy_lower_bound_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hedgingstrategy',
            name='strategy_id',
            field=models.UUIDField(default=uuid.UUID('ab6867be-1842-42e1-972e-5fe37aa81fd5'), editable=False),
        ),
    ]
