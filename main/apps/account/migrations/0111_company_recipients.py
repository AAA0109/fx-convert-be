# Generated by Django 4.2.11 on 2024-05-23 19:22

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0110_alter_autopilotdata_account_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='recipients',
            field=models.ManyToManyField(blank=True, related_name='recipients_companies', to=settings.AUTH_USER_MODEL),
        ),
    ]