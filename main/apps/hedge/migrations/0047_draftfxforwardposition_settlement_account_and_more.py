# Generated by Django 4.2 on 2023-09-24 17:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hedge', '0046_remove_draftfxforwardposition_delivery_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftfxforwardposition',
            name='settlement_account',
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name='draftfxforwardposition',
            name='beneficiary',
            field=models.TextField(null=True),
        ),
    ]
