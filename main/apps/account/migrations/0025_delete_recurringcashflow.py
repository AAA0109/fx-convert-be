# Generated by Django 3.2.8 on 2022-07-04 15:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0024_auto_20220704_1418'),
    ]

    operations = [
        migrations.DeleteModel(
            name='RecurringCashflow',
        ),
    ]