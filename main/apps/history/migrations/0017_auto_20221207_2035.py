# Generated by Django 3.2.8 on 2022-12-08 01:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0016_auto_20221031_0017'),
    ]

    operations = [
        migrations.RenameField(
            model_name='companysnapshot',
            old_name='realized_pnl',
            new_name='demo_change_in_realized_pnl',
        ),
        migrations.RenameField(
            model_name='companysnapshot',
            old_name='unrealized_pnl',
            new_name='demo_total_realized_pnl',
        ),
        migrations.AddField(
            model_name='companysnapshot',
            name='live_change_in_realized_pnl',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='companysnapshot',
            name='live_total_realized_pnl',
            field=models.FloatField(default=0),
        ),
    ]
