# Generated by Django 3.2.8 on 2022-10-31 15:01

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0054_delete_deposit'),
        ('currency', '0002_auto_20220702_1908'),
        ('margin', '0003_alter_fxspotmargin_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Deposit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('amount', models.FloatField()),
                ('method', models.CharField(choices=[('achus', 'ACHUS'), ('achca', 'ACHCA'), ('wire', 'WIRE')], max_length=11)),
                ('broker_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.brokeraccount')),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]
