# Generated by Django 4.2.10 on 2024-02-20 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0011_ticket_rfq_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='external_quote_id',
            field=models.TextField(blank=True, null=True),
        ),
    ]
