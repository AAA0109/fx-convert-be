# Generated by Django 4.2.10 on 2024-02-23 14:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0023_ticket_auth_time_ticket_auth_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='queue',
            name='source',
            field=models.TextField(blank=True, null=True),
        ),
    ]
