# Generated by Django 3.2.8 on 2023-08-07 21:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0002_country_use_in_average'),
    ]

    operations = [
        migrations.AlterField(
            model_name='country',
            name='use_in_average',
            field=models.BooleanField(default=True),
        ),
    ]
