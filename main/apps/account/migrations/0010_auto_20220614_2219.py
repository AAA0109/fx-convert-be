# Generated by Django 3.2.8 on 2022-06-14 22:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0009_merge_20220613_2102'),
    ]

    operations = [
        migrations.AddField(
            model_name='cashflow',
            name='original',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='revision', to='account.cashflow'),
        ),
        migrations.AddField(
            model_name='cashflow',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='child', to='account.cashflow'),
        ),
        migrations.AddField(
            model_name='cashflow',
            name='status',
            field=models.IntegerField(choices=[(1, 'Pending'), (2, 'Live')], default=1),
        ),
    ]
