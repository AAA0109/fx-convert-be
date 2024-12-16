import gzip
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
    from main.apps.marketdata.models import FxOption, FxOptionStrategy


    df_option_strategy = FxOptionStrategy.get_df(data_cut_id=62830)
    df_option = FxOption.get_df(data_cut_id=63332)

    print(df_option_strategy.head())
    print(df_option_strategy.columns)
    print(df_option.head())
    print(df_option.columns)


