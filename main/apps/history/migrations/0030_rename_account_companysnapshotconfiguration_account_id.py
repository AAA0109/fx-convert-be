# Generated by Django 4.2.10 on 2024-03-16 16:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0029_companysnapshotconfiguration'),
    ]

    operations = [
        migrations.RenameField(
            model_name='companysnapshotconfiguration',
            old_name='account',
            new_name='account_id',
        ),
    ]