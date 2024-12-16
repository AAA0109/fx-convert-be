# Generated by Django 3.2.8 on 2023-05-19 06:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataprovider', '0009_profile_days'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataprovider',
            name='provider_handler',
            field=models.CharField(choices=[('reuters', 'Reuters'), ('ice', 'ICE'), ('corpay', 'CorPay'), ('ibkr', 'IBKR')], default=None, max_length=255),
        ),
        migrations.AlterField(
            model_name='profile',
            name='file_format',
            field=models.CharField(choices=[('csv', 'csv'), ('xml', 'xml'), ('fixml', 'fixml'), ('json', 'json'), ('api', 'api'), ('html', 'html')], default='csv', max_length=10),
        ),
    ]