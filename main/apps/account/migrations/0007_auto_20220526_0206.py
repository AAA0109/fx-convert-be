# Generated by Django 3.2.8 on 2022-05-26 02:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0006_remove_company_ibkr_account_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='cashflow',
            name='description',
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name='cashflow',
            name='name',
            field=models.CharField(max_length=60, null=True),
        ),
        migrations.CreateModel(
            name='InstallmentCashflow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('installment_name', models.CharField(max_length=255)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.account')),
                ('cashflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.cashflow')),
            ],
            options={
                'verbose_name_plural': 'installment cashflows',
            },
        ),
    ]