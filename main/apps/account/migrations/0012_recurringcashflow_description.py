# Generated by Django 3.2.8 on 2022-06-22 00:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0011_alter_cashflow_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='recurringcashflow',
            name='description',
            field=models.TextField(null=True),
        ),
    ]
