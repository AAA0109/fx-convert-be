# Generated by Django 4.2.11 on 2024-05-14 18:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker', '0001_currencyfee_broker_cost_currencyfee_rev_share'),
    ]

    operations = [
        migrations.AddField(
            model_name='currencyfee',
            name='broker_fee',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='currencyfee',
            name='pangea_fee',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='currencyfee',
            name='wire_fee',
            field=models.FloatField(default=0.0),
        ),
    ]
