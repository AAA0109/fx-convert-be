# Generated by Django 4.2.7 on 2024-02-15 01:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0097_merge_20240130_0159"),
    ]

    operations = [
        migrations.AddField(
            model_name="parachutedata",
            name="floating_pnl_fraction",
            field=models.FloatField(default=0.0),
        ),
    ]
