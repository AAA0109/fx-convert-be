# Generated by Django 4.2.3 on 2024-01-06 20:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0090_merge_20231220_2044"),
    ]

    operations = [
        migrations.AlterField(
            model_name="account",
            name="strategy",
            field=models.IntegerField(
                choices=[(0, "Spot Hedging"), (1, "Parachute"), (2, "Hard Limits")],
                default=0,
            ),
        ),
    ]