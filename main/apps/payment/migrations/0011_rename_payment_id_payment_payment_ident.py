# Generated by Django 4.2.11 on 2024-05-23 19:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0010_payment_payment_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='payment',
            old_name='payment_id',
            new_name='payment_ident',
        ),
    ]
