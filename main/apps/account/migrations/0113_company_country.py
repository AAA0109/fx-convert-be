# Generated by Django 4.2.15 on 2024-09-06 21:11

from django.db import migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0112_remove_user_accounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='country',
            field=django_countries.fields.CountryField(blank=True, default='US', max_length=2, null=True),
        ),
    ]
