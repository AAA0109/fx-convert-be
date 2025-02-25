# Generated by Django 3.2.8 on 2023-07-28 02:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0077_company_rep'),
        ('hedge', '0041_draftfxforwardposition_beneficiary'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftfxforwardposition',
            name='estimated_fx_forward_price',
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='fxforwardposition',
            name='cashflow',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='account.cashflow'),
        ),
    ]
