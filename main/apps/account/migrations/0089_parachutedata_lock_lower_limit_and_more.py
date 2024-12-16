# Generated by Django 4.2.3 on 2023-12-19 02:07

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0088_merge_20231215_0319"),
    ]

    operations = [
        migrations.AddField(
            model_name="parachutedata",
            name="lock_lower_limit",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="cashflow",
            name="created",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="created"
            ),
        ),
        migrations.AlterField(
            model_name="draftcashflow",
            name="created",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="created"
            ),
        ),
    ]