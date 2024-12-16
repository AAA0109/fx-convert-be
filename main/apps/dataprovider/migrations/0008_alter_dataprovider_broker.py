# Generated by Django 3.2.8 on 2022-07-02 19:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0022_auto_20220702_1908'),
        ('dataprovider', '0007_profile_data_cut_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataprovider',
            name='broker',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='account.broker'),
        ),
    ]
