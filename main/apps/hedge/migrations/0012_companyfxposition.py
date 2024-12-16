# Generated by Django 3.2.8 on 2022-09-12 00:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0050_auto_20220909_0151'),
        ('currency', '0002_auto_20220702_1908'),
        ('hedge', '0011_delete_fxspotmargin'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyFxPosition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('record_time', models.DateTimeField()),
                ('positions_type', models.IntegerField(choices=[(1, 'Demo'), (2, 'Live')], default=1)),
                ('amount', models.FloatField(default=0.0)),
                ('total_price', models.FloatField(default=0.0, null=True)),
                ('broker', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fxbroker', to='account.broker')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fxcompany', to='account.company')),
                ('fxpair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='company_fxpair', to='currency.fxpair')),
            ],
            options={
                'verbose_name_plural': 'company_fxpositions',
                'unique_together': {('record_time', 'company', 'positions_type', 'broker', 'fxpair')},
            },
        ),
    ]