# Generated by Django 3.2.8 on 2023-08-08 23:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('corpay', '0015_auto_20230805_2116'),
    ]

    operations = [
        migrations.CreateModel(
            name='CurrencyDefinition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('p10', models.BooleanField(default=False)),
                ('wallet', models.BooleanField(default=False)),
                ('wallet_api', models.BooleanField(default=False)),
                ('ndf', models.BooleanField(default=False)),
                ('currency', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
            ],
        ),
    ]