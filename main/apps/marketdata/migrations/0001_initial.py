# Generated by Django 3.2.8 on 2022-05-06 00:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('currency', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CmAsset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('units', models.CharField(max_length=50, null=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
            ],
            options={
                'verbose_name_plural': 'Cm Assets',
            },
        ),
        migrations.CreateModel(
            name='CmInstrument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expiry', models.DateField()),
                ('expiry_label', models.CharField(max_length=30, null=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.cmasset')),
            ],
            options={
                'unique_together': {('asset', 'expiry')},
            },
        ),
        migrations.CreateModel(
            name='DataCut',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cut_time', models.DateTimeField(unique=True)),
                ('cut_type', models.IntegerField(choices=[(1, 'Eod'), (2, 'Intra')])),
            ],
        ),
        migrations.CreateModel(
            name='FxEstimator',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.IntegerField(choices=[(1, 'Ewma'), (2, 'Gas')], default=1)),
                ('tag', models.CharField(max_length=255)),
                ('parameters', models.CharField(max_length=255, null=True)),
            ],
            options={
                'unique_together': {('tag',)},
            },
        ),
        migrations.CreateModel(
            name='IrCurve',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('family', models.IntegerField(choices=[(1, 'Ois'), (2, 'Ibor')])),
                ('name', models.CharField(max_length=255)),
                ('long_name', models.CharField(max_length=255)),
                ('basis_convention', models.IntegerField(choices=[(1, 'Act 360'), (2, 'Act 365'), (3, 'Thirty 360'), (4, 'Thirty 365'), (5, 'Act Act')])),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
            ],
            options={
                'unique_together': {('currency', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Issuer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='VirtualCut',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_type', models.IntegerField(choices=[(1, 'Eod'), (2, 'Spot')])),
                ('actual_cut', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='actual_cut', to='marketdata.datacut')),
                ('virtual_cut', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='virtual_cut_handle', to='marketdata.datacut')),
            ],
        ),
        migrations.CreateModel(
            name='OptionStrategy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('tenor', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=15)),
                ('strategy', models.CharField(max_length=10)),
                ('offset', models.CharField(max_length=10)),
                ('bid_value', models.FloatField(null=True)),
                ('ask_value', models.FloatField(null=True)),
                ('mid_value', models.FloatField(null=True)),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Option',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('tenor', models.CharField(max_length=10)),
                ('expiry', models.DateField(null=True)),
                ('expiry_days', models.IntegerField()),
                ('strike', models.FloatField(null=True)),
                ('call_put', models.CharField(max_length=1, null=True)),
                ('delta', models.FloatField(null=True)),
                ('spot', models.FloatField()),
                ('depo_base', models.FloatField()),
                ('depo_quote', models.FloatField()),
                ('bid_vol', models.FloatField(null=True)),
                ('ask_vol', models.FloatField(null=True)),
                ('mid_vol', models.FloatField(null=True)),
                ('bid_price', models.FloatField(null=True)),
                ('ask_price', models.FloatField(null=True)),
                ('mid_price', models.FloatField(null=True)),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FxMarketConvention',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('min_lot_size', models.FloatField()),
                ('pair', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
        ),
        migrations.CreateModel(
            name='EqAsset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('is_index', models.BooleanField(default=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
            ],
            options={
                'verbose_name_plural': 'eq_assets',
            },
        ),
        migrations.CreateModel(
            name='Eq',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.eqasset')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CmSpot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('mid_price', models.FloatField(null=True)),
                ('bid_price', models.FloatField(null=True)),
                ('ask_price', models.FloatField(null=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.cmasset')),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
            ],
        ),
        migrations.CreateModel(
            name='CmInstrumentData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('mid_price', models.FloatField(null=True)),
                ('bid_price', models.FloatField(null=True)),
                ('ask_price', models.FloatField(null=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.cmasset')),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('instrument', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.cminstrument')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OISRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('tenor', models.CharField(max_length=10)),
                ('maturity', models.DateField()),
                ('maturity_days', models.IntegerField(null=True)),
                ('rate', models.FloatField()),
                ('rate_bid', models.FloatField(null=True)),
                ('rate_ask', models.FloatField(null=True)),
                ('fixing_rate', models.FloatField(null=True)),
                ('spread', models.FloatField(null=True)),
                ('spread_index', models.CharField(max_length=10, null=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
                ('curve', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='marketdata.ircurve')),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
            ],
            options={
                'abstract': False,
                'unique_together': {('data_cut', 'maturity', 'curve')},
            },
        ),
        migrations.CreateModel(
            name='IrDiscount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('maturity', models.DateField()),
                ('maturity_days', models.IntegerField(null=True)),
                ('discount', models.FloatField(null=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
                ('curve', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='marketdata.ircurve')),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
            ],
            options={
                'ordering': ['data_cut', 'curve', 'maturity'],
                'unique_together': {('data_cut', 'maturity', 'curve')},
            },
        ),
        migrations.CreateModel(
            name='IBORRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('tenor', models.CharField(max_length=10)),
                ('maturity', models.DateField()),
                ('maturity_days', models.IntegerField(null=True)),
                ('rate', models.FloatField()),
                ('rate_bid', models.FloatField(null=True)),
                ('rate_ask', models.FloatField(null=True)),
                ('zero_rate', models.FloatField(null=True)),
                ('instrument', models.CharField(max_length=20, null=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
                ('curve', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='marketdata.ircurve')),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
            ],
            options={
                'abstract': False,
                'unique_together': {('data_cut', 'maturity', 'curve')},
            },
        ),
        migrations.CreateModel(
            name='GovBond',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('tenor', models.CharField(max_length=10)),
                ('maturity', models.DateField()),
                ('maturity_days', models.IntegerField(null=True)),
                ('ytm', models.FloatField()),
                ('price', models.FloatField()),
                ('coupon', models.FloatField()),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('issuer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.issuer')),
            ],
            options={
                'unique_together': {('data_cut', 'tenor', 'issuer')},
            },
        ),
        migrations.CreateModel(
            name='FxSpotVol',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('vol', models.FloatField()),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('estimator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.fxestimator')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'unique_together': {('data_cut', 'pair', 'estimator')},
            },
        ),
        migrations.CreateModel(
            name='FxSpotRangeIntra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('open', models.FloatField(null=True)),
                ('open_bid', models.FloatField(null=True)),
                ('open_ask', models.FloatField(null=True)),
                ('low', models.FloatField(null=True)),
                ('low_bid', models.FloatField(null=True)),
                ('low_ask', models.FloatField(null=True)),
                ('high', models.FloatField(null=True)),
                ('high_bid', models.FloatField(null=True)),
                ('high_ask', models.FloatField(null=True)),
                ('close', models.FloatField(null=True)),
                ('close_bid', models.FloatField(null=True)),
                ('close_ask', models.FloatField(null=True)),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'abstract': False,
                'unique_together': {('data_cut', 'pair')},
            },
        ),
        migrations.CreateModel(
            name='FxSpotRangeEod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('open', models.FloatField(null=True)),
                ('open_bid', models.FloatField(null=True)),
                ('open_ask', models.FloatField(null=True)),
                ('low', models.FloatField(null=True)),
                ('low_bid', models.FloatField(null=True)),
                ('low_ask', models.FloatField(null=True)),
                ('high', models.FloatField(null=True)),
                ('high_bid', models.FloatField(null=True)),
                ('high_ask', models.FloatField(null=True)),
                ('close', models.FloatField(null=True)),
                ('close_bid', models.FloatField(null=True)),
                ('close_ask', models.FloatField(null=True)),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'abstract': False,
                'unique_together': {('data_cut', 'pair')},
            },
        ),
        migrations.CreateModel(
            name='FxSpotRange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('open', models.FloatField(null=True)),
                ('open_bid', models.FloatField(null=True)),
                ('open_ask', models.FloatField(null=True)),
                ('low', models.FloatField(null=True)),
                ('low_bid', models.FloatField(null=True)),
                ('low_ask', models.FloatField(null=True)),
                ('high', models.FloatField(null=True)),
                ('high_bid', models.FloatField(null=True)),
                ('high_ask', models.FloatField(null=True)),
                ('close', models.FloatField(null=True)),
                ('close_bid', models.FloatField(null=True)),
                ('close_ask', models.FloatField(null=True)),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'abstract': False,
                'unique_together': {('data_cut', 'pair')},
            },
        ),
        migrations.CreateModel(
            name='FxSpotIntra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('rate', models.FloatField(null=True)),
                ('rate_bid', models.FloatField(null=True)),
                ('rate_ask', models.FloatField(null=True)),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'abstract': False,
                'unique_together': {('data_cut', 'pair')},
            },
        ),
        migrations.CreateModel(
            name='FxSpotEod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('rate', models.FloatField(null=True)),
                ('rate_bid', models.FloatField(null=True)),
                ('rate_ask', models.FloatField(null=True)),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'abstract': False,
                'unique_together': {('data_cut', 'pair')},
            },
        ),
        migrations.CreateModel(
            name='FxSpotCovariance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('covariance', models.FloatField()),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('estimator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.fxestimator')),
                ('pair_1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cross_vol_pair_1', to='currency.fxpair')),
                ('pair_2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cross_vol_pair_2', to='currency.fxpair')),
            ],
            options={
                'unique_together': {('data_cut', 'pair_1', 'pair_2', 'estimator')},
            },
        ),
        migrations.CreateModel(
            name='FxSpotBenchmark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('rate', models.FloatField(null=True)),
                ('rate_bid', models.FloatField(null=True)),
                ('rate_ask', models.FloatField(null=True)),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'abstract': False,
                'unique_together': {('data_cut', 'pair')},
            },
        ),
        migrations.CreateModel(
            name='FxSpot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('rate', models.FloatField(null=True)),
                ('rate_bid', models.FloatField(null=True)),
                ('rate_ask', models.FloatField(null=True)),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'abstract': False,
                'unique_together': {('data_cut', 'pair')},
            },
        ),
        migrations.CreateModel(
            name='FxForward',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('tenor', models.CharField(max_length=4)),
                ('rate', models.FloatField(null=True)),
                ('rate_bid', models.FloatField(null=True)),
                ('rate_ask', models.FloatField(null=True)),
                ('fwd_points', models.FloatField(null=True)),
                ('fwd_points_bid', models.FloatField(null=True)),
                ('fwd_points_ask', models.FloatField(null=True)),
                ('depo_base', models.FloatField()),
                ('depo_quote', models.FloatField()),
                ('data_cut', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketdata.datacut')),
                ('pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'unique_together': {('data_cut', 'pair', 'tenor')},
            },
        ),
    ]
