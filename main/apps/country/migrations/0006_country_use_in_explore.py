# Generated by Django 4.2.3 on 2023-10-02 17:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0005_country_strictness_of_capital_controls_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='use_in_explore',
            field=models.BooleanField(default=False),
        ),
    ]
