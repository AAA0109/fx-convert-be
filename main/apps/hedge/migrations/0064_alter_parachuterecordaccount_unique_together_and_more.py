# Generated by Django 4.2.7 on 2024-01-29 18:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hedge', '0063_merge_20240124_1910'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='parachuterecordaccount',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='parachutespotpositions',
            unique_together=set(),
        ),
    ]
