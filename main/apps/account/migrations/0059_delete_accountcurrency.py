# Generated by Django 3.2.8 on 2022-11-12 20:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0058_user_phone_confirmed'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AccountCurrency',
        ),
    ]