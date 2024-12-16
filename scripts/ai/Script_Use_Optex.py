import os
import sys
from datetime import timedelta

from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Date import Date

logger = get_logger(level=logging.INFO)

if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()
    from main.apps.ai.services.asset.optex.predictor import OptexAssetPredictorService

    pair = "EUR/USD"
    now = Date.now()
    start_time = now.replace(minute=now.minute - (now.minute % 15), second=0, microsecond=0)
    end_time = start_time + timedelta(hours=int(24 * 7))
    rate_start = 1.05  # rate at start (enter current rate when this algo is run)

    wait_condition = OptexAssetPredictorService().wait_condition(
        pair=pair,
        start_time=start_time,
        end_time=end_time,
        rate_start=rate_start
    )

    wait_time = wait_condition.wait_time
    expected_saving = wait_condition.expected_saving
    expected_saving_percentage = wait_condition.expected_saving_percentage
    upper_bound = wait_condition.upper_bound
    lower_bound = wait_condition.lower_bound
    regime = wait_condition.regime

    print("regime: ", regime)
    print("wait_time: ", wait_time)
    print("expected saving: ", expected_saving)
    print("expected saving percentage: ", expected_saving_percentage)
    print("upper_bound: ", upper_bound)
    print("rate_start: ", rate_start)
    print("lower_bound: ", lower_bound)
    print("upper-mid: ", upper_bound - rate_start)
    print("min-lower: ", rate_start - lower_bound)
