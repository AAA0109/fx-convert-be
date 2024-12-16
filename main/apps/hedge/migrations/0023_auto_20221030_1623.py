# Generated by Django 3.2.8 on 2022-10-30 16:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hedge', '0022_merge_20221030_1622'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyevent',
            name='has_account_fx_snapshot',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='companyevent',
            name='has_company_fx_snapshot',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='companyevent',
            name='has_hedge_action',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='companyfxposition',
            name='snapshot_event',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='hedge.companyevent'),
        ),
        migrations.AlterField(
            model_name='companyfxposition',
            name='record_time',
            field=models.DateTimeField(null=True),
        ),
    ]
