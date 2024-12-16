# Generated by Django 4.2.10 on 2024-02-19 23:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0009_ticket_clearing_broker_ticket_exec_broker'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='error_message',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ticket',
            name='execution_status',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ticket',
            name='payment_memo',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ticket',
            name='quote_user',
            field=models.TextField(blank=True, null=True),
        ),
    ]