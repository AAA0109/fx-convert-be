# Generated by Django 4.2.10 on 2024-02-19 16:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0008_rename_qutoe_source_ticket_quote_source_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='clearing_broker',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ticket',
            name='exec_broker',
            field=models.TextField(blank=True, null=True),
        ),
    ]
