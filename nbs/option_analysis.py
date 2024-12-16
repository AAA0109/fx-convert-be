import pandas as pd
from sqlalchemy import create_engine, text
from datetime import timedelta
import os
import sys
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 2000)

def get_datacut_df():
    datacut_query = """Select * from marketdata_datacut"""
    conn = create_engine('postgresql+psycopg2://ryanhayashino:qwerty@localhost:5432/pangea_dump_6_12').connect()
    datacut = pd.read_sql_query(sql=text(datacut_query), con=conn)
    conn.close()
    datacut = datacut.rename(columns={"id": "data_cut_id"})
    return datacut

def get_forward_details(datacut, select_pairs, select_tenors, cut_types):
    # initiate empty list used to append rows to final df
    data_missing = []
    data_detail = []
    day_delta = timedelta(days=1)
    day_we_delta = timedelta(days=3)
    start_query = """Select min(date), max(date) from marketdata_option
                where pair_id= :pair"""
    query = """Select date, extract(dow from date) as dow, pair_id, tenor,call_put, data_cut_id from marketdata_option
                where pair_id= :pair and tenor = :tenor
                and date >= :start and date <= :stop
                order by date ASC"""
    # datacut = get_datacut_df()

    for pair in select_pairs:
        # query min/max dates per pair
        conn = create_engine('postgresql+psycopg2://ryanhayashino:qwerty@localhost:5432/pangea_dump_6_12').connect()
        date_df = pd.read_sql_query(sql=text(start_query).bindparams(pair=pair), con=conn)
        start = date_df['min'].iloc[0]
        stop = date_df['max'].iloc[0]
        if (date_df.empty) | (start is None and stop is None):
            print("Pair Index Not found for: ", pair)
            data_detail.append([None, None, pair, None, None])
            continue
        else:
            for tenor in select_tenors:
                found_inx = []
                # query fx_forward by pair/tenor/start/stop
                conn = create_engine(
                    'postgresql+psycopg2://ryanhayashino:qwerty@localhost:5432/pangea_dump_6_12').connect()
                df = pd.read_sql_query(sql=text(query).bindparams(pair=pair, tenor=tenor, start=start, stop=stop), con=conn)
                conn.close()

                df = df.merge(datacut, on="data_cut_id", how="left")
                if df.empty:
                    data_detail.append([None, None, pair, tenor, None, None])
                    print("Missing Data Pair: ", pair, " Tenor: ", tenor)
                else:
                    for cut in cut_types:
                        for option_type in option_types:
                            df_cut = df[(df['cut_type'] == cut) & (df['call_put'] == option_type)]
                            print("Pair:", pair, "Tenor:", tenor, "cut_type:", cut, " rows:", len(df_cut))
                            # collect earliest record date for pair/tenor
                            if len(df_cut) == 0:
                                # exception: no instance of cut
                                data_detail.append([None, None, pair, tenor, option_type, cut])
                                continue
                            else:
                                # collect earliest record date for pair/tenor
                                data_detail.append([start, stop, pair, tenor, option_type, cut])
                            # iterate with big windows looking for missing dates
                            big_win = 15
                            for big_window in df_cut.rolling(window=big_win):
                                dow_sum = big_window['dow'].sum()
                                # look for instance of missing days of week, ignore windows without sufficient data
                                if dow_sum != (big_win*3) and len(big_window) >= big_win:
                                    mini_win = 2
                                    # iterate with small windows when big window is suspicious
                                    for mini_window in big_window.rolling(window=mini_win):
                                        # ignore values if they have already been accounted for
                                        if mini_window.index[0] in found_inx:
                                            continue
                                        elif len(mini_window) == mini_win:
                                            dow_base = mini_window['dow'].iloc[0]
                                            dow_lead = mini_window['dow'].iloc[1]
                                            dow_delta = dow_lead - dow_base
                                            if (dow_base == 5) & (dow_delta == -4):
                                                continue
                                            elif dow_delta == 1:
                                                continue
                                            else:
                                                # print(mini_window) #remove after testing
                                                if mini_window.index[0] not in found_inx:
                                                    found_inx.append(mini_window.index[0])
                                                beg_date = mini_window['date'].iloc[0].date()
                                                end_date = mini_window['date'].iloc[1].date()
                                                count = 0
                                                while beg_date != end_date:
                                                    count += 1
                                                    # print(beg_date) #remove after testing
                                                    # save missing dates, later added to missing_df
                                                    if count > 1:
                                                        data_missing.append([beg_date, int(beg_date.isoweekday()), pair, tenor, option_type, cut])
                                                    # add 1 day or 3 days if weekend
                                                    if int(beg_date.isoweekday()) == 5:
                                                        beg_date += day_we_delta
                                                    else:
                                                        beg_date += day_delta
                                        else: pass
                                else: pass

    detail_df = pd.DataFrame(data_detail, columns=['earliest_date', 'latest_date', 'pair_id', 'tenor', 'call_put', 'cut_type'])
    missing_df = pd.DataFrame(data_missing, columns=['date', 'dow', 'pair_id', 'tenor', 'call_put', 'cut_type'])

    return detail_df, missing_df


# create pair mapping
if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")
    # Setup django
    import django
    django.setup()
    from main.apps.currency.models import FxPair
    # create mapping
    pair_map = {}
    for pair in FxPair.objects.all():
        pair_map[pair.id] = {'name': pair.name, 'base_id': pair.base.id, 'base_name': pair.base.get_mnemonic(), 'quote_id': pair.quote.id, 'quote_name': pair.quote.get_mnemonic()}

def get_currency_info(df, pair_map):
    df['pair_name'] = None
    df['base_id'] = None
    df['base_name'] = None
    df['quote_id'] = None
    df['quote_name'] = None

    for id in df.pair_id.unique():
        df.loc[df['pair_id'] == id, 'pair_name'] = pair_map[id]['name']
        df.loc[df['pair_id'] == id, 'base_id'] = pair_map[id]['base_id']
        df.loc[df['pair_id'] == id, 'base_name'] = pair_map[id]['base_name']
        df.loc[df['pair_id'] == id, 'quote_id'] = pair_map[id]['quote_id']
        df.loc[df['pair_id'] == id, 'quote_name'] = pair_map[id]['quote_name']
    return df

all_pairs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 45,
             46, 47, 48, 49, 50, 51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
             72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93]
all_tenors = ['4Y', '7M', 'SW', '1Y', '10Y', 'SN', '18M', '6M', '5Y', '7Y', '6W', '1W', '5M', '10M', '3Y', '8M',
              '2Y', '11M', '1M', '15M', 'TN', '3M', '2M', '9M', '3W', '4M', '2W', 'ON', '1D']
cut_types = [1,3]
call_put = ['C', 'P', 'A']

datacut = get_datacut_df()
detail_df, missing_df = get_forward_details(datacut, all_pairs, all_tenors, call_put, cut_types)

df_missing_final = get_currency_info(missing_df, pair_map)
print(df_missing_final.head())
df_missing_final.to_csv("../storage/csv/missing data analysis/missing_data_option.csv", index=False)

df_detail_final = get_currency_info(detail_df, pair_map)
print(df_detail_final.head())
df_detail_final.to_csv("../storage/csv/missing data analysis/details_data_option.csv", index=False)
