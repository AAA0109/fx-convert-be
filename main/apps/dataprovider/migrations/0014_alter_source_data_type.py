# Generated by Django 4.2 on 2023-08-16 08:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataprovider', '0013_alter_source_data_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='source',
            name='data_type',
            field=models.CharField(choices=[('local_storage', 'Local Storage'), ('sftp', 'SFTP'), ('rest', 'REST API'), ('gcp', 'Google Cloud'), ('ibkr_tws', 'IBKR TWS'), ('ibkr_web', 'IBKR Web')], default='local_storage', max_length=255),
        ),
    ]
