# Generated by Django 3.2.8 on 2022-10-08 16:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0052_alter_brokeraccount_company'),
        ('currency', '0002_auto_20220702_1908'),
        ('hedge', '0015_auto_20221007_0129'),
    ]

    operations = [
        migrations.AlterField(
            model_name='companyfxposition',
            name='broker_account',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fxbroker_account', to='account.brokeraccount'),
        ),
        migrations.AlterUniqueTogether(
            name='companyfxposition',
            unique_together={('record_time', 'company', 'broker_account', 'fxpair')},
        ),
        migrations.RemoveField(
            model_name='companyfxposition',
            name='positions_type',
        ),
    ]
