# Generated by Django 3.2.8 on 2023-08-18 07:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketdata', '0017_auto_20230627_1735'),
    ]

    operations = [
        migrations.AddField(
            model_name='corpayfxforward',
            name='tenor_days',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]