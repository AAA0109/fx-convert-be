# Generated by Django 3.2.8 on 2023-07-29 19:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hedge', '0042_auto_20230728_0229'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='draftfxforwardposition',
            name='fxpair',
        ),
    ]