# Generated by Django 4.2.11 on 2024-07-03 00:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monex', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='monexcompanysettings',
            name='monex_entity_id',
        ),
        migrations.AddField(
            model_name='monexcompanysettings',
            name='company_name',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='monexcompanysettings',
            name='customer_id',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='monexcompanysettings',
            name='entity_id',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.DeleteModel(
            name='MonexUserSettings',
        ),
    ]
