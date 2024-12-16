# Generated by Django 3.2.8 on 2023-05-03 21:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketdata', '0011_fxmarketconvention_is_supported'),
    ]

    operations = [
        migrations.CreateModel(
            name='CorpayFxForward',
            fields=[
                ('fxforward_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='marketdata.fxforward')),
            ],
            options={
                'abstract': False,
            },
            bases=('marketdata.fxforward',),
        ),
    ]