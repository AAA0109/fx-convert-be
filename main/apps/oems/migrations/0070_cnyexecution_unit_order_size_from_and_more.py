# Generated by Django 4.2.11 on 2024-04-19 16:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0069_ticket_trade_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='cnyexecution',
            name='unit_order_size_from',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='cnyexecution',
            name='unit_order_size_to',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='ticket',
            name='underlying_instrument',
            field=models.TextField(blank=True, null=True),
        ),
    ]
