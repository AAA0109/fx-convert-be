# Generated by Django 4.2.11 on 2024-05-30 15:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payment', '0015_alter_payment_payment_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='auth_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payment_auth_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='payment',
            name='create_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payment_create_user', to=settings.AUTH_USER_MODEL),
        ),
    ]
