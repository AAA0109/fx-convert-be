# Generated by Django 3.2.8 on 2023-06-23 01:35

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
            name='SupportedFxPairs',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('fx_pair_type', models.CharField(choices=[('p20', 'P20'), ('wallet', 'Wallet'), ('other', 'Other')], max_length=60)),
                ('fx_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.fxpair')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]