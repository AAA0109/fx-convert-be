# Generated by Django 3.2.8 on 2023-06-24 17:38

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0006_auto_20230323_0038'),
        ('corpay', '0008_alter_fxbalancedetail_fx_balance'),
    ]

    operations = [
        migrations.CreateModel(
            name='FxForwardCosts',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('min_notional', models.FloatField(default=1000)),
                ('average_volume', models.FloatField()),
                ('notional_low', models.FloatField()),
                ('notional_high', models.FloatField()),
                ('cost_in_bps', models.FloatField()),
                ('fxpair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]
