# Generated by Django 3.2.8 on 2022-09-11 19:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0050_auto_20220909_0151'),
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Aum',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('daily_aum', models.FloatField()),
                ('rolling_aum', models.FloatField()),
                ('rolling_window', models.IntegerField()),
                ('actual_window', models.IntegerField()),
                ('recorded', models.DateTimeField(auto_now_add=True)),
                ('date', models.DateField()),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aum_companies', to='account.company')),
            ],
            options={
                'verbose_name_plural': 'aums',
                'unique_together': {('company', 'date')},
            },
        ),
    ]
