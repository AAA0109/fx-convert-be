# Generated by Django 4.2.3 on 2023-10-05 21:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hedge', '0049_draftfxforwardposition_purpose_of_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftfxforwardposition',
            name='destination_account_type',
            field=models.CharField(choices=[('W', 'Wire'), ('E', 'iACH'), ('C', 'FXBalance')], max_length=1, null=True),
        ),
    ]
