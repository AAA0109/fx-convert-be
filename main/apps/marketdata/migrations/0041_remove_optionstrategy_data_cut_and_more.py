# Generated by Django 4.2.11 on 2024-06-21 13:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("marketdata", "0040_merge_20240528_1747"),
    ]

    operations = [
        migrations.RemoveField(model_name="optionstrategy", name="data_cut",),
        migrations.RemoveField(model_name="optionstrategy", name="pair",),
        migrations.DeleteModel(name="Option",),
        migrations.DeleteModel(name="OptionStrategy",),
    ]
