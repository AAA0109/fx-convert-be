# Generated by Django 3.2.8 on 2022-06-07 23:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0007_auto_20220526_0206'),
    ]

    operations = [
        migrations.AlterField(
            model_name='brokeraccount',
            name='account_type',
            field=models.IntegerField(choices=[(1, 'Live'), (2, 'Paper')]),
        ),
    ]
