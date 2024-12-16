# Generated by Django 3.2.8 on 2022-05-09 20:22

from django.db import migrations, models
import django.db.models.deletion
import main.apps.broker.models.broker


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrokerAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('broker_account_name', models.CharField(max_length=255)),
                ('account_type', models.IntegerField(verbose_name=main.apps.broker.models.broker.BrokerAccount.AccountType)),
                ('broker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.broker')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.company')),
            ],
        ),
    ]
