# Generated by Django 3.2.8 on 2022-06-17 04:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0012_alter_cashflow_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashflow',
            name='status',
            field=models.IntegerField(choices=[(0, 'Inactive'), (1, 'Draft'), (2, 'Pending Activation'), (3, 'Active'), (4, 'Pending Deactivation')], default=1),
        ),
    ]
