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
    from main.apps.dataprovider.scripts.helper.utils import get_all_related_objects

    cut_types = [
        DataCut.CutType.EOD,
    ]
    filter_hour = 0
    datacut_qs = DataCut.objects.filter(cut_type__in=cut_types, cut_time__hour=filter_hour)
    print(f"number of datacut to delete: {datacut_qs.count()}")
    print("============Preview===============")
    datacut_df = pd.DataFrame(list(datacut_qs.values())).rename(columns={"id": "data_cut_id"})
    print(datacut_df)
    print("=====================================")

    all_related_objects = {}
    for cut in datacut_qs:
        all_related_objects[cut.id] = get_all_related_objects(cut)

    for key1, val1 in all_related_objects.items():
        for key2, val2 in val1.items():
            if val2.exists():
                print(f'{key2} is exist | count {val2.count()}')


