# Generated by Django 3.2.8 on 2022-11-20 19:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0066_alter_extendinvitationtoken_invitation_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='is_hidden',
            field=models.BooleanField(default=False),
        ),
    ]
