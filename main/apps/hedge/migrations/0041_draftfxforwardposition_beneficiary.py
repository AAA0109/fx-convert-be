# Generated by Django 3.2.8 on 2023-07-06 00:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('corpay', '0012_auto_20230706_0019'),
        ('hedge', '0040_alter_fxforwardposition_cashflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftfxforwardposition',
            name='beneficiary',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='corpay.beneficiary'),
        ),
    ]
