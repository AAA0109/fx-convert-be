# Generated by Django 4.2.11 on 2024-06-05 00:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('account', '0112_remove_user_accounts'),
    ]

    operations = [
        migrations.CreateModel(
            name='NiumSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_hash_id', models.TextField(blank=True, null=True)),
                ('api_key', models.TextField(blank=True, null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.company')),
            ],
        ),
    ]
