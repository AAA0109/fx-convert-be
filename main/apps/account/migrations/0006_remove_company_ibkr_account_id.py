# Generated by Django 3.2.8 on 2022-05-10 05:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0005_rename_account_id_company_ibkr_account_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='company',
            name='ibkr_account_id',
        ),
    ]