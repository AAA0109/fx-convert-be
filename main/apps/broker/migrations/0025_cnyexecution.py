# Generated by Django 4.2.15 on 2024-10-18 10:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0108_cashflow_cashflowgenerator_payment'),
        ('broker', '0024_deliverytime'),
    ]

    operations = [
        migrations.CreateModel(
            name='CnyExecution',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('oems.cnyexecution',),
        ),
    ]
