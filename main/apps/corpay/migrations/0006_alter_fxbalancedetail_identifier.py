# Generated by Django 3.2.8 on 2023-05-25 16:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corpay', '0005_auto_20230525_1602'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fxbalancedetail',
            name='identifier',
            field=models.CharField(max_length=60),
        ),
    ]
