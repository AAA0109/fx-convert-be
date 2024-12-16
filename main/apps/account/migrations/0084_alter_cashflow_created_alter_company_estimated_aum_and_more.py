# Generated by Django 4.2.3 on 2023-12-05 22:02

from django.db import migrations, models
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0083_alter_company_estimated_aum'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashflow',
            name='created',
            field=models.DateTimeField(verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='company',
            name='estimated_aum',
            field=models.CharField(blank=True, choices=[('0_10m', '0-$10,000,000'), ('10m_25m', '$10,000,000 - $25,000,000'), ('25m_50m', '$25,000,000 - $50,000,000'), ('50m+', '$50,000,000+')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='company',
            name='service_interested_in',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('fx_hedging', 'FX Hedging'), ('wallet', 'Wallet'), ('payment', 'Payment & Transfer')], max_length=25, null=True),
        ),
        migrations.AlterField(
            model_name='draftcashflow',
            name='created',
            field=models.DateTimeField(verbose_name='created'),
        ),
    ]
