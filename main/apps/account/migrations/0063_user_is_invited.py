# Generated by Django 3.2.8 on 2022-11-19 07:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0062_alter_companyjoinrequest_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_invited',
            field=models.BooleanField(default=False),
        ),
    ]