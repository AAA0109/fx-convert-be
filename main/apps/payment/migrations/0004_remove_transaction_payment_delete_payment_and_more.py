# Generated by Django 4.2.10 on 2024-03-26 05:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0003_payment_payment_status'),
        ('billing', '0010_alter_fee_payment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='payment',
        ),
        migrations.DeleteModel(
            name='Payment',
        ),
        migrations.DeleteModel(
            name='Transaction',
        ),
    ]