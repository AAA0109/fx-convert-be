# Generated by Django 3.2.8 on 2022-08-15 00:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0043_alter_installmentcashflow_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftcashflow',
            name='action',
            field=models.CharField(choices=[('CREATE', 'Create'), ('UPDATE', 'Update'), ('DELETE', 'Delete')], default='CREATE', max_length=10),
            preserve_default=False,
        ),
    ]
