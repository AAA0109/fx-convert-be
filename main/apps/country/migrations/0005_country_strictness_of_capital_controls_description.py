# Generated by Django 3.2.8 on 2023-09-28 02:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0004_auto_20230925_2355'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='strictness_of_capital_controls_description',
            field=models.TextField(blank=True, null=True, verbose_name='Description for Strictness of Capital Controls'),
        ),
    ]
