# Generated by Django 4.2.10 on 2024-03-21 06:46

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('webhook', '0002_auto_20240321_0636'),
    ]

    operations = [
        migrations.AddField(
            model_name='webhook',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]
