import os
import sys

if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()
    from main.apps.marketdata.models import DataCut
    from main.apps.dataprovider.scripts.utils import get_revision_df, get_all_related_objects

    revision_df, df_sorted = get_revision_df()
    qs_need_adjustment = DataCut.objects.filter(id__in=revision_df['data_cut_id'].tolist()).order_by('id')
    all_related_objects = {}
    for cut in qs_need_adjustment:
        all_related_objects[cut.id] = get_all_related_objects(cut)

    print("=====================================")
    for key1, val1 in all_related_objects.items():
        print(f' DataCut id: {key1}')
        for key2, val2 in val1.items():
            if val2.exists():
                print(f'Related to {key2} | count {val2.count()}')
