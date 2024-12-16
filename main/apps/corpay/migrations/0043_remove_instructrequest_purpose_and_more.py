# Generated by Django 4.2.3 on 2024-01-17 10:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corpay', '0042_instructrequest_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='instructrequest',
            name='purpose',
        ),
        migrations.AddField(
            model_name='instructrequest',
            name='from_delivery_method',
            field=models.CharField(choices=[('W', 'Wire'), ('E', 'iACH'), ('C', 'FXBalance')], null=True),
        ),
        migrations.AddField(
            model_name='instructrequest',
            name='from_purpose',
            field=models.CharField(choices=[('All', 'All'), ('Allocation', 'Allocation'), ('Fee', 'Fee'), ('Spot', 'Spot'), ('Spot_trade', 'Spot Trade'), ('Drawdown', 'Drawdown')], null=True),
        ),
        migrations.AddField(
            model_name='instructrequest',
            name='same_settlement_currency',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='instructrequest',
            name='to_delivery_method',
            field=models.CharField(choices=[('W', 'Wire'), ('E', 'iACH'), ('C', 'FXBalance')], null=True),
        ),
        migrations.AddField(
            model_name='instructrequest',
            name='to_purpose',
            field=models.CharField(choices=[('All', 'All'), ('Allocation', 'Allocation'), ('Fee', 'Fee'), ('Spot', 'Spot'), ('Spot_trade', 'Spot Trade'), ('Drawdown', 'Drawdown')], null=True),
        ),
        migrations.AlterField(
            model_name='instructrequest',
            name='delivery_method',
            field=models.CharField(choices=[('W', 'Wire'), ('E', 'iACH'), ('C', 'FXBalance')], null=True),
        ),
    ]
