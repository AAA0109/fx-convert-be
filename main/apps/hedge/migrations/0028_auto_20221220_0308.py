# Generated by Django 3.2.8 on 2022-12-20 03:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0002_auto_20220702_1908'),
        ('hedge', '0027_accountdesiredpositions')
    ]

    operations = [
        migrations.AddField(
            model_name='accountdesiredpositions',
            name='company_hedge_action',
            field=models.ForeignKey(default=490, on_delete=django.db.models.deletion.CASCADE, to='hedge.companyhedgeaction'),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='accountdesiredpositions',
            unique_together={('company_hedge_action', 'account', 'fxpair')},
        ),
        migrations.RemoveField(
            model_name='accountdesiredpositions',
            name='snapshot_event',
        ),
    ]
