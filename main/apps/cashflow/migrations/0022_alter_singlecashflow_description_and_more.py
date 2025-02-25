# Generated by Django 4.2.15 on 2024-08-29 23:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cashflow', '0021_singlecashflow_transaction_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='singlecashflow',
            name='description',
            field=models.TextField(blank=True, help_text='A description of the cashflow', null=True),
        ),
        migrations.AlterField(
            model_name='singlecashflow',
            name='name',
            field=models.CharField(blank=True, help_text='A name for the cashflow', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='singlecashflow',
            name='ticket_id',
            field=models.UUIDField(blank=True, help_text='the ticket ID associated with this single cashflow', null=True),
        ),
        migrations.AlterField(
            model_name='singlecashflow',
            name='transaction_date',
            field=models.DateField(blank=True, help_text="Payment's cashflow transaction date", null=True),
        ),
    ]
