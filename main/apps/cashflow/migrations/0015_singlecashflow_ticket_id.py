# Generated by Django 4.2.11 on 2024-04-11 21:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cashflow', '0014_merge_20240410_1902'),
    ]

    operations = [
        migrations.AddField(
            model_name='singlecashflow',
            name='ticket_id',
            field=models.UUIDField(help_text='the ticket ID associated with this single cashflow', null=True),
        ),
    ]