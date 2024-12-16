# Generated by Django 3.2.8 on 2022-11-21 17:21

from django.db import migrations

from main.apps.account.models.account import Account


def update_switch_account_low_high(apps, schema_editor):
    low_accounts = Account.objects.filter(name='low')
    high_accounts = Account.objects.filter(name='high')
    low_accounts.update(name='high_temp')
    high_accounts.update(name='low_temp')
    low_accounts = Account.objects.filter(name='high_temp')
    high_accounts = Account.objects.filter(name='low_temp')
    low_accounts.update(name='high')
    high_accounts.update(name='low')


class Migration(migrations.Migration):
    dependencies = [
        ('account', '0067_account_is_hidden'),
    ]

    operations = [
        migrations.RunPython(update_switch_account_low_high)
    ]
