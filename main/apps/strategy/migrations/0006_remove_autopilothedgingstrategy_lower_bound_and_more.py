# Generated by Django 4.2.10 on 2024-03-05 00:48

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0103_merge_20240224_0039'),
        ('strategy', '0005_hedgingstrategy_lock_side'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='autopilothedgingstrategy',
            name='lower_bound',
        ),
        migrations.RemoveField(
            model_name='autopilothedgingstrategy',
            name='upper_bound',
        ),
        migrations.AddField(
            model_name='autopilothedgingstrategy',
            name='lower_target',
            field=models.FloatField(help_text='The lower target for the strategy used to define a stop-loss bound', null=True),
        ),
        migrations.AddField(
            model_name='autopilothedgingstrategy',
            name='upper_target',
            field=models.FloatField(help_text='The upper target for the strategy used to define a take-profit bound', null=True),
        ),
        migrations.AddField(
            model_name='hedgingstrategy',
            name='slug',
            field=models.SlugField(default='default'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='hedgingstrategy',
            name='strategy_id',
            field=models.UUIDField(default=uuid.UUID('7fb66f61-3348-4b0e-9da9-13f5bc933b44'), editable=False),
        ),
        migrations.AlterField(
            model_name='autopilothedgingstrategy',
            name='risk_reduction',
            field=models.FloatField(help_text='The ratio of the amount to be hedged (0.0 - 1,0)'),
        ),
        migrations.AlterUniqueTogether(
            name='hedgingstrategy',
            unique_together={('company', 'slug')},
        ),
    ]
