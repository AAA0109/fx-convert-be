# Generated by Django 4.2.10 on 2024-03-06 16:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0039_alter_ticket_rfq_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cnyexecution',
            name='fut_base',
        ),
    ]
