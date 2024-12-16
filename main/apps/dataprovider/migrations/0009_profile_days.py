# Generated by Django 3.2.8 on 2022-08-18 19:08

from django.db import migrations
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('dataprovider', '0008_alter_dataprovider_broker'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='days',
            field=multiselectfield.db.fields.MultiSelectField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')], default=[0, 1, 2, 3, 4], help_text='Days to import data on', max_length=13),
        ),
    ]