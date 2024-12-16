# Generated by Django 4.2.15 on 2024-08-29 22:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settlement', '0041_alter_wallet_account_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='beneficiary',
            name='bank_region',
            field=models.TextField(blank=True, help_text='State, Province, etc.', null=True),
        ),
    ]
