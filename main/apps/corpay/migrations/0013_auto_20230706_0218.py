# Generated by Django 3.2.8 on 2023-07-06 02:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0077_company_rep'),
        ('corpay', '0012_auto_20230706_0019'),
    ]

    operations = [
        migrations.AlterField(
            model_name='corpaysettings',
            name='company',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='account.company'),
        ),
        migrations.DeleteModel(
            name='CreditUtilization',
        ),
    ]