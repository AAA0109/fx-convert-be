# Generated by Django 3.2.8 on 2022-10-04 01:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ibkr', '0014_ibkraccountsummary'),
    ]

    operations = [
        migrations.AddField(
            model_name='ibkraccountsummary',
            name='account_type',
            field=models.CharField(default='None', max_length=255),
            preserve_default=False,
        ),
    ]