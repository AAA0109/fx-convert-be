# Generated by Django 4.2.10 on 2024-02-29 18:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('strategy', '0003_selfguidedhedgingstrategy'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='SelfGuidedHedgingStrategy',
            new_name='SelfDirectedHedgingStrategy',
        ),
        migrations.AlterField(
            model_name='hedgingstrategy',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'), ('live', 'Live'), ('canceled', 'Cancelled')], default='draft', help_text='The status of the strategy', max_length=24),
        ),
    ]
