import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('currency', '0018_alter_currency_options_alter_fxpair_options'),
        ('corpay', '0039_merge_0037_spotrate_0038_corpaysettings_max_horizon'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='UpdateNDF',
            new_name='ManualForwardRequest'
        ),
        migrations.AlterField(
            model_name='ManualForwardRequest',
            name='request',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ndf_request',
                                       to='corpay.updaterequest'),
        ),
        migrations.AlterField(
            model_name='updaterequest',
            name='type',
            field=models.CharField(choices=[
                ('cashflow_details', 'Cashflow Details'),
                ('risk_details', 'Risk Details'),
                ('drawdown', 'drawdown'),
                ('nsf', 'Non sellable forward'),
                ('ndf', 'Non deliverable forward')
            ]),
        ),
    ]
