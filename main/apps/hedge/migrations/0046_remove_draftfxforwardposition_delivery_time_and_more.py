# Generated by Django 4.2 on 2023-08-25 01:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hedge', '0045_auto_20230813_1808'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='draftfxforwardposition',
            name='delivery_time',
        ),
        migrations.AlterField(
            model_name='draftfxforwardposition',
            name='estimated_fx_forward_price',
            field=models.FloatField(null=True),
        ),
    ]
