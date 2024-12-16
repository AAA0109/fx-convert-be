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

def get_spotdetails(select_pairs, cut_types):
    # initiate empty list used to append rows to final df
    data_missing = []
    data_detail = []
    day_delta = timedelta(days=1)
    day_we_delta = timedelta(days=3)
    start_query = """Select date,extract(dow from date) as dow, data_cut_id from marketdata_fxspot
                where pair_id= :pair
                order by date ASC"""
    data_cut = get_datacut_df()

    for pair in range(0,select_pairs):   #range(44,all_pairs)
        pair = pair + 1
        if pair == 53:
            continue
        # query min/max dates per pair
        conn = create_engine('postgresql+psycopg2://ryanhayashino:qwerty@localhost:5432/pangea_dump_6_12').connect()
        df = pd.read_sql_query(sql=text(start_query).bindparams(pair=pair), con=conn)
        conn.close()

        df = df.merge(datacut, on="data_cut_id", how="left")
        start = df['date'].min()
        stop = df['date'].max()

        if (df.empty) | (start is None and stop is None):
            print("Pair Index Not found for: ", pair)
            data_detail.append([None, None, pair, None])
            continue
        else:
            found_inx = []
            for cut in cut_types:
                df_cut = df[df['cut_type'] == cut]

                if len(df_cut) == 0:
                    # exception: no instance of cut
                    data_detail.append([None, None, pair, cut])
                else:
                    # collect earliest record date for pair/tenor
                    data_detail.append([start, stop, pair, cut])

                # iterate with big windows looking for missing dates
                big_win = 15
                print("Pair: ", pair, " rows:", len(df_cut), " cut_type:", cut)
                for big_window in df_cut.rolling(window=big_win):
                    dow_sum = big_window['dow'].sum()
                    # look for instance of missing days of week, ignore windows without sufficient data
                    if (dow_sum != (big_win*3) and len(big_window) >= big_win) | (6.0 in list(big_window['dow'])):
                        mini_win = 2
                        # iterate with small windows when big window is suspicious
                        for mini_window in big_window.rolling(window=mini_win):
                            # ignore values if they have already been accounted for
                            if mini_window.index[0] in found_inx:
                                continue
                            elif (len(mini_window) == mini_win):
                                dow_base = mini_window['dow'].iloc[0]
                                dow_lead = mini_window['dow'].iloc[1]
                                dow_delta = dow_lead - dow_base
                                if (dow_base == 5) & (dow_delta == -4):
                                    continue
                                elif (dow_base > 5) | (dow_lead > 5):
                                    if (dow_base > 5):
                                        if mini_window.index[0] not in found_inx:
                                            found_inx.append(mini_window.index[0])
                                            miss_date = mini_window['date'].iloc[0].date()
                                            cut = mini_window['cut_type'].iloc[0]
                                            data_missing.append([miss_date, int(dow_base), pair, cut])
                                        else: continue
                                    else:
                                        if mini_window.index[1] not in found_inx:
                                            found_inx.append(mini_window.index[1])
                                            miss_date = mini_window['date'].iloc[1].date()
                                            cut = mini_window['cut_type'].iloc[1]
                                            data_missing.append([miss_date, int(dow_lead), pair, cut])
                                        else: continue
                                elif dow_delta == 1:
                                    continue
                                else:
                                    if mini_window.index[0] not in found_inx:
                                        found_inx.append(mini_window.index[0])
                                    beg_date = mini_window['date'].iloc[0].date()
                                    end_date = mini_window['date'].iloc[1].date()
                                    count = 0
                                    while beg_date <= end_date:
                                        count += 1
                                        # save missing dates, later added to missing_df
                                        if count > 1:
                                            data_missing.append([beg_date, int(beg_date.isoweekday()), pair, cut])
                                        # add 1 day or 3 days if weekend
                                        if int(beg_date.isoweekday()) == 5:
                                            beg_date += day_we_delta
                                        else:
                                            beg_date += day_delta
                            else: pass
                    else: pass

    detail_df = pd.DataFrame(data_detail, columns = ['earliest_date', 'latest_date', 'pair_id', 'cut_type'])
    missing_df = pd.DataFrame(data_missing, columns = ['date', 'dow', 'pair_id', 'cut_type'])

    return detail_df, missing_df

# FxPair related details
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
        pair_map[pair.id] = {'name': pair.name, 'base_id': pair.base.id, 'base_name': pair.base.get_mnemonic(), "quote_id":pair.quote.id, 'quote_name': pair.quote.get_mnemonic()}


select_pairs = 93
cut_types = [1,3]
detail_df, missing_df = get_spotdetails(select_pairs, cut_types)

detail_df = get_currency_info(detail_df, pair_map)
detail_df.to_csv("../storage/csv/missing data analysis/details_data_fxspot.csv", index=False)
missing_df = get_currency_info(missing_df, pair_map)
missing_df.to_csv("../storage/csv/missing data analysis/missing_data_fxspot.csv", index=False)
