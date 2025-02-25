# Generated by Django 4.2.15 on 2024-09-20 10:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0029_auto_20240825_0646'),
        ('broker', '0019_alter_currencyfee_options_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='currencyfee',
            unique_together={('broker', 'buy_currency', 'sell_currency', 'instrument_type')},
        ),
        migrations.AlterField(
            model_name='currencyfee',
            name='cost',
            field=models.FloatField(null=True),
        ),
    ]
