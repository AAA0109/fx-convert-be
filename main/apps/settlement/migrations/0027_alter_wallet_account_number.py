# Generated by Django 4.2.11 on 2024-07-02 19:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settlement', '0026_wallet_last_synced_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallet',
            name='account_number',
            field=models.CharField(help_text='The account number associated with the wallet', max_length=100),
        ),
    ]