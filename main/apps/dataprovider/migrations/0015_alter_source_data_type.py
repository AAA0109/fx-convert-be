# Generated by Django 3.2.8 on 2023-08-19 12:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataprovider', '0014_alter_source_data_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='source',
            name='data_type',
            field=models.CharField(choices=[('local_storage', 'Local Storage'), ('sftp', 'SFTP'), ('rest', 'REST API'), ('gcp', 'Google Cloud'), ('ibkr_tws', 'IBKR TWS'), ('ibkr_web', 'IBKR Web'), ('corpay', 'CorPay API')], default='local_storage', max_length=255),
        ),
    ]