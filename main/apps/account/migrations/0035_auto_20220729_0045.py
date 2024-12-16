# Generated by Django 3.2.8 on 2022-07-29 00:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0034_merge_20220719_0216'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashflow',
            name='date',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='cashflow',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='draftcashflow',
            name='date',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='draftcashflow',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
