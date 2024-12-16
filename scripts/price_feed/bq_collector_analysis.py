import os
import sys
from datetime import datetime, timedelta
from django.conf import settings
from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)

if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()
    import pandas as pd

    # Define your project, dataset, and table IDs
    project_id = settings.GCP_PROJECT_ID
    dataset_id = 'marketdata'
    table_id = 'development-QuoteTick'
    source = 'CORPAY'
    instrument = 'USDJPY-SPOT'

    # Calculate dates for filtering
    today = datetime.today().strftime('%Y-%m-%d')
    one_month_ago = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')

    query = f"""
    SELECT *
    FROM `{project_id}.{dataset_id}.{table_id}`
    WHERE source = '{source}' AND instrument = '{instrument}'
      AND time BETWEEN '{one_month_ago}' AND '{today}'
    """

    # Read data from BigQuery into a pandas DataFrame
    df = pd.read_gbq(query, project_id=project_id, dialect='standard')

    # Ensure the 'time' column is in datetime format
    df['time'] = pd.to_datetime(df['time'])

    # Calculate spread and mid prices
    df['spread'] = df['ask'] - df['bid']
    df['mid'] = (df['ask'] + df['bid']) / 2
    df['spread_ratio'] = df['spread'] / df['mid']

    # Extract the hour from the 'time' column
    df['hour'] = df['time'].dt.hour

    # Group by hour and calculate the required statistics
    hourly_df = df.groupby('hour')['spread_ratio'].agg(['min', 'max', 'mean', 'std']).reset_index()

    # Ensure there are 24 hourly buckets, filling missing hours with NaN
    full_hours = pd.DataFrame({'hour': range(24)})
    hourly_df = full_hours.merge(hourly_df, on='hour', how='left')

    print(hourly_df)

