# Generated by Django 3.2.8 on 2022-10-29 20:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hedge', '0020_currencymargin_date'),
    ]

    operations = [
        migrations.DeleteModel(
            name='FxRolloverRate',
        ),
    ]
