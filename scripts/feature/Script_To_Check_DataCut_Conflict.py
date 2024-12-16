import os
import sys

import pandas as pd

if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()
    from main.apps.marketdata.models import DataCut
    from django.db.models import Q

    from main.apps.dataprovider.scripts.utils import get_all_related_objects

    # hour=22
    # type=1
    hour=16
    type=3

    datacut_qs = DataCut.objects.filter(
        ~Q(cut_type=type)
    ).extra(
        where=["EXTRACT(HOUR FROM cut_time) = %s",
               "EXTRACT(MINUTE FROM cut_time) = %s",
               "EXTRACT(SECOND FROM cut_time) = %s"],
        params=[hour, 0, 0]
    )
    datacut_df = pd.DataFrame(list(datacut_qs.values()))
    all_related_objects = {}
    for cut in datacut_qs:
        all_related_objects[cut.id] = get_all_related_objects(cut)

    for key1, val1 in all_related_objects.items():
        for key2, val2 in val1.items():
            if val2.exists():
                print(f'data_cut_id: {key1} | {key2} is exist | count {val2.count()}')
