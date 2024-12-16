# Generated by Django 3.2.8 on 2023-08-20 23:01

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0007_auto_20230808_2148'),
        ('ibkr', '0022_auto_20230206_0753'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('symbol', models.CharField(max_length=10, null=True)),
                ('sec_type', models.CharField(max_length=10, null=True)),
                ('exchange', models.CharField(max_length=10, null=True)),
                ('future_start_date', models.DateTimeField(null=True)),
                ('ib_last_date', models.DateTimeField(null=True)),
                ('base_currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='contarct_base_currency', to='currency.currency')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]