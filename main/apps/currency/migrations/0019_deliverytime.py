# Generated by Django 4.2.3 on 2023-11-28 14:47

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0006_country_use_in_explore'),
        ('currency', '0018_alter_currency_options_alter_fxpair_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryTime',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('delivery_method', models.CharField(choices=[('W', 'Wire'), ('E', 'iACH'), ('C', 'FXBalance')], max_length=50)),
                ('delivery_sla', models.IntegerField()),
                ('deadline', models.TimeField()),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='country.country')),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]
