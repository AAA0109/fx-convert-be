# Generated by Django 4.2.10 on 2024-03-26 05:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0009_move_payment_and_transaction_data_to_billing'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fee',
            name='payment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fee_payments', to='billing.payment'),
        ),
    ]
