# Generated by Django 4.2.7 on 2024-01-26 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataprovider', '0021_alter_profile_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profileparalleloption',
            name='instrument',
            field=models.CharField(blank=True, choices=[('spot', 'Spot'), ('forward', 'Forward')], default=None, null=True),
        ),
    ]
