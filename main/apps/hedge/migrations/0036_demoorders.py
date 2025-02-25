# Generated by Django 3.2.8 on 2023-03-02 01:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0004_auto_20230228_0256'),
        ('hedge', '0035_accountdesiredpositions_pre_liquidity_amount'),
    ]

    operations = [
        migrations.CreateModel(
            name='DemoOrders',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unrounded_amount', models.FloatField()),
                ('requested_amount', models.FloatField()),
                ('total_price', models.FloatField(null=True)),
                ('company_hedge_action', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hedge.companyhedgeaction')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
        ),
    ]
