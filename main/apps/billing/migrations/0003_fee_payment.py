# Generated by Django 3.2.8 on 2022-09-13 01:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0001_initial'),
        ('billing', '0002_aum'),
    ]

    operations = [
        migrations.AddField(
            model_name='fee',
            name='payment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fee_payments', to='payment.payment'),
        ),
    ]
