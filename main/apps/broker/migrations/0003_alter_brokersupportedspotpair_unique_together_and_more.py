# Generated by Django 4.2.3 on 2024-02-14 10:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('broker', '0002_auto_20240105_0032'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='brokersupportedspotpair',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='brokersupportedspotpair',
            name='broker',
        ),
        migrations.RemoveField(
            model_name='brokersupportedspotpair',
            name='pair',
        ),
        migrations.DeleteModel(
            name='BrokerSupportedForwardPair',
        ),
        migrations.DeleteModel(
            name='BrokerSupportedSpotPair',
        ),
    ]
