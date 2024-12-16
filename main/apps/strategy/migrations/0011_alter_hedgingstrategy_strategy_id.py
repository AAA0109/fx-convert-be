# Generated by Django 4.2.10 on 2024-03-06 16:27

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('strategy', '0010_alter_hedgingstrategy_strategy_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hedgingstrategy',
            name='strategy_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
