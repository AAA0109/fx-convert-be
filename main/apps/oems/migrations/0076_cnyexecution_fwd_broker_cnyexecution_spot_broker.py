# Generated by Django 4.2.11 on 2024-05-06 19:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0075_ticket_instrument_fields_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cnyexecution',
            name='fwd_broker',
            field=models.TextField(default='CORPAY'),
        ),
        migrations.AddField(
            model_name='cnyexecution',
            name='spot_broker',
            field=models.TextField(default='CORPAY_MP'),
        ),
    ]
