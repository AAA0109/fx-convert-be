# Generated by Django 3.2.8 on 2022-11-19 08:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('drf_simple_invite', '0001_initial'),
        ('account', '0063_user_is_invited'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExtendInvitationToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invitation_token', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='drf_simple_invite.invitationtoken')),
                ('inviter', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]