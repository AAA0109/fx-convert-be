# Generated by Django 4.2.11 on 2024-07-02 18:44

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('broker', '0004_merge_20240702_1833'),
        ('account', '0112_remove_user_accounts'),
        ('currency', '0027_convert_ccys'),
        ('settlement', '0022_beneficiarybroker'),
    ]

    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('wallet_id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Unique identifier of the wallet')),
                ('external_id', models.TextField(help_text='The external wallet identifier')),
                ('name', models.CharField(help_text='The name of the wallet', max_length=100)),
                ('description', models.TextField(blank=True, help_text='A description of the wallet', null=True)),
                ('account_number', models.CharField(help_text='The account number associated with the wallet', max_length=100, unique=True)),
                ('hidden', models.BooleanField(default=False, help_text='Whether the wallet is hidden, can be use for internal fee collection')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended'), ('closed', 'Closed')], default='active', help_text='The status of the wallet', max_length=20)),
                ('type', models.CharField(choices=[('settlement', 'Settlement'), ('wallet', 'Wallet'), ('virtual_account', 'Virtual Account'), ('managed', 'Managed')], default='wallet', help_text='The type of the wallet', max_length=20)),
                ('broker', models.ForeignKey(help_text='The broker the wallet is associated with', on_delete=django.db.models.deletion.PROTECT, related_name='wallets', to='broker.broker')),
                ('company', models.ForeignKey(help_text='The company the wallet belongs to', on_delete=django.db.models.deletion.PROTECT, related_name='wallets', to='account.company')),
                ('currency', models.ForeignKey(help_text='The currency of the wallet', on_delete=django.db.models.deletion.PROTECT, to='currency.currency')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='BeneficiaryDefaults',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('beneficiary', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='settlement.beneficiary')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.company')),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='currency.currency')),
            ],
        ),
    ]
