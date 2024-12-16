# Generated by Django 4.2.11 on 2024-04-19 01:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0008_alter_payment_cashflow_generator'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='destination_account_method',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='origin_account_method',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
