# Generated by Django 4.2.10 on 2024-02-27 21:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0029_queue_resp_at_alter_ticket_tenor_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='transaction_id',
            field=models.TextField(blank=True, help_text='Unique identifier for the transaction.', null=True),
        ),
    ]
