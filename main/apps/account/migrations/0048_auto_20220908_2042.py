# Generated by Django 3.2.8 on 2022-09-08 20:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0047_auto_20220907_0344'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='hs_company_id',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='hs_contact_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
