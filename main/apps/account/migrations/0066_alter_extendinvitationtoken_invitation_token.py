# Generated by Django 3.2.8 on 2022-11-19 08:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('drf_simple_invite', '0001_initial'),
        ('account', '0065_alter_extendinvitationtoken_invitation_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='extendinvitationtoken',
            name='invitation_token',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='extend', to='drf_simple_invite.invitationtoken'),
        ),
    ]