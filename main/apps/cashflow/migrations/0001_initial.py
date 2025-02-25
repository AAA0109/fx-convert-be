# Generated by Django 4.2.7 on 2024-02-20 18:30

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('currency', '0019_deliverytime'),
        ('account', '0102_remove_hedgingstrategy_company_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SingleCashFlow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('pay_date', models.DateTimeField(help_text='The date the cashflow is paid or received')),
                ('amount', models.FloatField(help_text='The amount of the cashflow')),
                ('status', models.CharField(choices=[('draft', 'DRAFT'), ('pending', 'PENDING'), ('approved', 'APPROVED'), ('live', 'LIVE'), ('canceled', 'CANCELED')], default='draft', help_text='The status of the cashflow', max_length=24)),
                ('name', models.CharField(help_text='A name for the cashflow', max_length=255, null=True)),
                ('description', models.TextField(help_text='A description of the cashflow', null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cashflows', to='account.company')),
                ('currency', models.ForeignKey(help_text='The currency of the cashflow', on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_currency', to='currency.currency')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]
