import os
import sys
import pandas as pd
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 2000)

if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")
    # Setup django
    import django
    django.setup()
    from main.apps.currency.models import FxPair
    #create mapping
    pair_map = {}
    for pair in FxPair.objects.all():
        pair_map[pair.id] = {'name': pair.name, 'base_id': pair.base.id, 'base_name': pair.base.get_mnemonic(), "quote_id":pair.quote.id, 'quote_name': pair.quote.get_mnemonic()}


def get_currency_info(df, pair_map):
    df['pair_name'] = None
    df['base_id'] = None
    df['base_name'] = None
    df['quote_id'] = None
    df['quote_name'] = None

    for id in df.pair_id.unique():
        df.loc[df['pair_id'] == id,'pair_name'] = pair_map[id]['name']
        df.loc[df['pair_id'] == id,'base_id'] = pair_map[id]['base_id']
        df.loc[df['pair_id'] == id,'base_name'] = pair_map[id]['base_name']
        df.loc[df['pair_id'] == id,'quote_id'] = pair_map[id]['quote_id']
        df.loc[df['pair_id'] == id,'quote_name'] = pair_map[id]['quote_name']
    return df

df = pd.read_csv("../storage/csv/analysis/missing_data_fxspot_full.csv")
df_final = get_currency_info(df, pair_map)
print(df_final.head())
df_final.to_csv("../storage/csv/analysis/fxspot_missing_data_test_test.csv", index=False)

df = pd.read_csv("../storage/csv/analysis/details_data_fxspot_full.csv")
df_final = get_currency_info(df, pair_map)
print(df_final.head())
df_final.to_csv("../storage/csv/analysis/fxspot_details_data_test_test.csv", index=False)
