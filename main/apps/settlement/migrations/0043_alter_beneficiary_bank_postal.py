# Generated by Django 4.2.15 on 2024-09-03 22:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settlement', '0042_alter_beneficiary_bank_region'),
    ]

    operations = [
        migrations.AlterField(
            model_name='beneficiary',
            name='bank_postal',
            field=models.TextField(blank=True, help_text='Bank postal code', null=True),
        ),
    ]
