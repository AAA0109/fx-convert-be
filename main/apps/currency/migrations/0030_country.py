# Generated by Django 4.2.15 on 2024-10-11 11:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0006_country_use_in_explore'),
        ('currency', '0029_auto_20240825_0646'),
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
            ],
            options={
                'verbose_name_plural': 'Countries',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('country.country',),
        ),
    ]