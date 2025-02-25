# Generated by Django 4.2.11 on 2024-05-30 00:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0112_remove_user_accounts'),
        ('broker', 'add_corpay_fees_20240513'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrokerCompany',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('broker', models.CharField(choices=[('CORPAY', 'CORPAY'), ('IBKR', 'IBKR'), ('CORPAY_MP', 'CORPAY_MP'), ('VERTO', 'VERTO'), ('NIUM', 'NIUM'), ('AZA', 'AZA'), ('MONEX', 'MONEX'), ('CONVERA', 'CONVERA'), ('OFX', 'OFX'), ('XE', 'XE'), ('OANDA', 'OANDA'), ('AIRWALLEX', 'AIRWALLEX')], max_length=255)),
                ('brokers', models.ManyToManyField(to='broker.broker')),
                ('company', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='account.company')),
            ],
            options={
                'unique_together': {('broker', 'company')},
            },
        ),
    ]
