# Generated by Django 3.2.8 on 2023-01-16 01:36

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('auditlog', '0010_alter_logentry_timestamp'),
        ('account', '0069_user_phone_otp_code'),
        ('history', '0019_activity_bankstatement_feepayment_trades'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('activity_type', models.CharField(choices=[('UserAdded', 'USER_ADDED'), ('PasswordReset', 'PASSWORD_RESET'), ('EmailChange', 'EMAIL_CHANGE'), ('AccountCreated', 'ACCOUNT_CREATED'), ('IbVerified', 'IB_VERIFIED'), ('CompanyVerified', 'COMPANY_VERIFIED'), ('PaymentCreated', 'PAYMENT_CREATED'), ('PaymentChanged', 'PAYMENT_CHANGED')], max_length=64)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.company')),
                ('log_entry', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='auditlog.logentry')),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='bankstatement',
            name='company',
        ),
        migrations.RemoveField(
            model_name='feepayment',
            name='cashflow',
        ),
        migrations.RemoveField(
            model_name='feepayment',
            name='company',
        ),
        migrations.RemoveField(
            model_name='trades',
            name='company',
        ),
        migrations.RemoveField(
            model_name='trades',
            name='pair',
        ),
        migrations.DeleteModel(
            name='Activity',
        ),
        migrations.DeleteModel(
            name='BankStatement',
        ),
        migrations.DeleteModel(
            name='FeePayment',
        ),
        migrations.DeleteModel(
            name='Trades',
        ),
    ]
