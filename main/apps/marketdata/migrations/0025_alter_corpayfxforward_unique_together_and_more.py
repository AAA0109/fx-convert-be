# Generated by Django 4.2.3 on 2023-12-02 03:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0013_auto_20231106_2229'),
        ('marketdata', '0024_merge_0022_merge_20231101_1703_0023_corpayfxspot'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='corpayfxforward',
            unique_together={('data_cut', 'pair', 'tenor')},
        ),
        migrations.AlterUniqueTogether(
            name='corpayfxspot',
            unique_together={('data_cut', 'pair')},
        ),
        migrations.RemoveField(
            model_name='corpayfxforward',
            name='company',
        ),
        migrations.RemoveField(
            model_name='corpayfxspot',
            name='company',
        ),
    ]
