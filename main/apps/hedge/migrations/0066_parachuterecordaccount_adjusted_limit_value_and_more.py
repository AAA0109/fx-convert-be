# Generated by Django 4.2.7 on 2024-02-15 01:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hedge", "0065_fxforwardposition_initial_pangea_forward_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="parachuterecordaccount",
            name="adjusted_limit_value",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="parachuterecordaccount",
            name="max_pnl",
            field=models.FloatField(default=0.0),
        ),
    ]