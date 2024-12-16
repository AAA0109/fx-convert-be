# Generated by Django 3.2.8 on 2023-08-13 18:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0077_company_rep'),
        ('hedge', '0044_merge_20230805_2055'),
    ]

    operations = [
        migrations.AlterField(
            model_name='draftfxforwardposition',
            name='status',
            field=models.CharField(choices=[('draft', 'DRAFT'), ('pending_activation', 'PENDING ACTIVATION'), ('active', 'ACTIVE')], default='draft', max_length=24),
        ),
        migrations.AlterField(
            model_name='fxforwardposition',
            name='cashflow',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.cashflow'),
        ),
    ]
