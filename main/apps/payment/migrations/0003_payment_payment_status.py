# Generated by Django 3.2.8 on 2022-10-06 01:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0002_rename_payment_id_transaction_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='payment_status',
            field=models.CharField(choices=[('initiated', 'Initiated'), ('success', 'Success'), ('error', 'Error')], default='initiated', max_length=24),
        ),
    ]
