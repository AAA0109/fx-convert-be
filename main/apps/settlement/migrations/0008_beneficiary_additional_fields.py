# Generated by Django 4.2.11 on 2024-05-24 02:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settlement', '0007_monexbeneficiary_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='beneficiary',
            name='additional_fields',
            field=models.JSONField(blank=True, help_text='Additional broker-specific fields as key-value pairs', null=True),
        ),
    ]
