# Generated by Django 3.2.8 on 2022-10-31 00:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0053_auto_20221019_2204'),
        ('currency', '0002_auto_20220702_1908'),
        ('history', '0015_reconciliationrecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='reconciliationrecord',
            name='is_live',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterUniqueTogether(
            name='reconciliationrecord',
            unique_together={('reference_time', 'fx_pair', 'company', 'is_live')},
        ),
    ]