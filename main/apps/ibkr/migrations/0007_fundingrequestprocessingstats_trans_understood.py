# Generated by Django 3.2.8 on 2022-09-18 07:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ibkr', '0006_auto_20220918_0706'),
    ]

    operations = [
        migrations.AddField(
            model_name='fundingrequestprocessingstats',
            name='trans_understood',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]