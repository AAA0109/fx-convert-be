# Generated by Django 4.2.10 on 2024-03-13 17:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oems', '0049_manualrequest_exec_text'),
    ]

    operations = [
        migrations.AlterField(
            model_name='manualrequest',
            name='time_in_force',
            field=models.CharField(choices=[('15min', '15min'), ('day', 'day'), ('gtc', 'gtc')], default='15min', max_length=5),
        ),
    ]
