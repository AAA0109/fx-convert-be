# Generated by Django 3.2.8 on 2023-08-09 01:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corpay', '0015_auto_20230805_2116'),
    ]

    operations = [
        migrations.AddField(
            model_name='beneficiary',
            name='is_withdraw',
            field=models.BooleanField(default=False),
        ),
    ]