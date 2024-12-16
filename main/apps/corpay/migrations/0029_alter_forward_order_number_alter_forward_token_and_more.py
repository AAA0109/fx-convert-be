# Generated by Django 4.2.3 on 2023-10-12 23:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0080_merge_20231009_2008'),
        ('corpay', '0028_forward_destination_account_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='forward',
            name='order_number',
            field=models.CharField(max_length=11),
        ),
        migrations.AlterField(
            model_name='forward',
            name='token',
            field=models.CharField(max_length=32),
        ),
        migrations.AlterField(
            model_name='forwardquote',
            name='cashflow',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='quote_cashflow', to='account.cashflow'),
        ),
        migrations.AlterField(
            model_name='forwardquote',
            name='quote_id',
            field=models.CharField(max_length=32),
        ),
    ]