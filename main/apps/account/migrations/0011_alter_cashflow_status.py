# Generated by Django 3.2.8 on 2022-06-17 00:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0010_auto_20220614_2219'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashflow',
            name='status',
            field=models.IntegerField(choices=[(0, 'Inactive'), (1, 'Pending Active'), (2, 'Active'), (3, 'Pending Deactivation')], default=1),
        ),
    ]
