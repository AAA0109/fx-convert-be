# Generated by Django 4.2.15 on 2024-10-11 11:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0022_alter_payment_payment_status'),
        ('settlement', '0050_alter_beneficiary_default_purpose'),
        ('account', '0114_company_postal_company_region'),
    ]

    operations = [
        migrations.CreateModel(
            name='Beneficiary',
            fields=[
            ],
            options={
                'verbose_name_plural': 'Beneficiaries',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('settlement.beneficiary',),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('payment.payment',),
        ),
        migrations.CreateModel(
            name='Wallet',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('settlement.wallet',),
        ),
    ]