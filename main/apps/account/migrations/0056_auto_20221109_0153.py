# Generated by Django 3.2.8 on 2022-11-09 01:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0055_alter_draftcashflow_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='activation_token',
            field=models.CharField(blank=True, max_length=60, null=True),
        ),
        migrations.AlterField(
            model_name='broker',
            name='name',
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='accounts',
            field=models.ManyToManyField(blank=True, to='account.Account'),
        ),
    ]
