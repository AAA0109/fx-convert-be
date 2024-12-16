import logging
from datetime import timedelta

import pandas as pd
from django.db import migrations, transaction

from main.apps.dataprovider.scripts.utils import is_dst

logger = logging.getLogger("root")


def fix_fxspotintra_datetime(apps, schema_editor):
    FxSpotIntra = apps.get_model('marketdata', 'FxSpotIntra')

    with transaction.atomic():
        fsi_df = pd.DataFrame(list(FxSpotIntra.objects.all().values()))
        if fsi_df.empty:
            logger.warning("No data found in FxSpotIntra table.")
            return
        fsi_df['is_dst'] = fsi_df['date'].apply(is_dst)
        fsi_df['new_date'] = fsi_df['date']

        # Adjust time to UTC
        fsi_df.loc[fsi_df['is_dst'], 'new_date'] -= timedelta(hours=4)
        fsi_df.loc[~fsi_df['is_dst'], 'new_date'] -= timedelta(hours=5)

        # Sort DataFrame by 'new_date' in descending order
        fsi_df.sort_values(by='date', ascending=True, inplace=True)

        for val in fsi_df['date'].unique():
            new_date = fsi_df.loc[fsi_df['date'] == val, 'new_date'].iloc[0]
            # Check if new_date already exists
            if not FxSpotIntra.objects.filter(date=new_date).exists():
                objs = FxSpotIntra.objects.filter(date=val)
                objs.update(date=new_date)
                logger.debug(f"Date updated: {val} changed to {new_date}.")

            else:
                logger.warning(f"Duplicate date found: {val}. New date {new_date} not applied.")


class Migration(migrations.Migration):
    dependencies = [
        ("dataprovider", "0028_alter_dataprovider_provider_handler"),
    ]

    operations = [
        migrations.RunPython(fix_fxspotintra_datetime)
    ]
