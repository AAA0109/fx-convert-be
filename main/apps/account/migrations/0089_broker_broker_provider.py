# Generated by Django 4.2.3 on 2023-12-20 07:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0088_broker_execution_method_alter_company_estimated_aum_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='broker',
            name='broker_provider',
            field=models.CharField(blank=True, choices=[('Corpay', 'Corpay'), ('IBKR', 'IBKR')], max_length=50),
        ),
    ]
