# Generated by Django 4.2.10 on 2024-03-12 13:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0021_merge_20240311_1922'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deliverytime',
            name='country',
            field=models.CharField(max_length=255),
        ),
    ]