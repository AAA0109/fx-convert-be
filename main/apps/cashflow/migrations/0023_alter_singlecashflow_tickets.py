# Generated by Django 4.2.15 on 2024-08-29 23:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0101_remove_cnyexecution_default_broker'),
        ('cashflow', '0022_alter_singlecashflow_description_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='singlecashflow',
            name='tickets',
            field=models.ManyToManyField(blank=True, null=True, to='oems.ticket'),
        ),
    ]