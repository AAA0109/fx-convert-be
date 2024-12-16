# Generated by Django 3.2.8 on 2023-02-13 22:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0070_company_onboarded'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashflow',
            name='status',
            field=models.CharField(choices=[('inactive', 'INACTIVE'), ('pending_activation', 'PENDING ACTIVATION'), ('active', 'ACTIVE'), ('pending_deactivation', 'PENDING_DEACTIVATION'), ('pending_payment', 'PENDING PAYMENT'), ('payment_fail', 'PAYMENT FAIL')], default='pending_activation', max_length=24),
        ),
    ]