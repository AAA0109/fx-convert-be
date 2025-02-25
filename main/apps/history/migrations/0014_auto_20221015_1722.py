# Generated by Django 3.2.8 on 2022-10-15 17:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0013_accountsnapshot_num_cashflows_in_window'),
    ]

    operations = [
        migrations.RenameField(
            model_name='companysnapshot',
            old_name='cashflow_abs_fwd',
            new_name='demo_cashflow_abs_fwd',
        ),
        migrations.AddField(
            model_name='companysnapshot',
            name='live_cashflow_abs_fwd',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='companysnapshot',
            name='num_demo_cashflows_in_windows',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='companysnapshot',
            name='num_live_cashflows_in_windows',
            field=models.IntegerField(default=0),
        ),
    ]
