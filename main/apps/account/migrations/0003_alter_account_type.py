# Generated by Django 3.2.8 on 2022-05-09 22:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_brokeraccount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='type',
            field=models.IntegerField(choices=[(0, 'Draft'), (1, 'Demo'), (2, 'Live')], default=1),
        ),
    ]
