# Generated by Django 3.2.8 on 2022-08-02 19:10

from django.db import migrations
import timezone_field.fields


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0038_alter_user_phone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='timezone',
            field=timezone_field.fields.TimeZoneField(blank=True, default='UTC', null=True),
        ),
    ]
