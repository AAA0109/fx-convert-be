# Generated by Django 4.2.11 on 2024-07-02 19:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settlement', '0023_wallet_beneficiarydefaults'),
    ]

    operations = [
        migrations.AddField(
            model_name='wallet',
            name='bank_name',
            field=models.CharField(blank=True, help_text='The name of the bank associated with the wallet', max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='wallet',
            name='broker_account_id',
            field=models.TextField(blank=True, help_text='The account identifier used by the broker for this account', null=True),
        ),
        migrations.AlterField(
            model_name='wallet',
            name='name',
            field=models.CharField(blank=True, help_text='The name of the wallet', max_length=100, null=True),
        ),
    ]