# Generated by Django 4.2.3 on 2023-12-07 20:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0018_alter_currency_options_alter_fxpair_options'),
        ('ibkr', '0030_auto_20231207_1755'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supportedfxpair',
            name='fxpair',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair'),
        ),
    ]
