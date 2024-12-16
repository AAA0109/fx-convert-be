import pandas as pd
from datetime import datetime
import datetime as dt
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 2000)

# df['year'] = pd.DatetimeIndex(df['date']).year
# print(df.shape)
# df2 = pd.read_csv("../storage/csv/analysis/missing_data_fxspot_full2.csv")
# print(df2.shape)
# df_final = pd.concat([df1,df2])
# print(df_final.shape)
# df_final.to_csv("../storage/csv/analysis/missing_data_fxspot5_30.csv", index=False)
# df = df.drop(df.columns[0], axis = 1)
# print(df['pair_id'].max())


# df2 = df.groupby(['pair_id','year'])['date'].count()
# df2 = df.groupby(['pair_id'])['date'].count()
# 12 ==ZAR #south africa
# 14== CHF #swiss franc

df = pd.read_csv("../storage/csv/analysis/fxforward_details_data")
df['earliest_date'] = pd.to_datetime(df['earliest_date'], format = "%Y/%m/%d %H:%M:%S")
df['latest_date'] = pd.to_datetime(df['latest_date'], format = "%Y/%m/%d %H:%M:%S")
df_missing = pd.read_csv("../storage/csv/analysis/fxforward_missing_data.csv")
df_missing['date'] = pd.to_datetime(df_missing['date'], format = "%Y/%m/%d", utc=False).dt.date
# df_missing['date'] = df_missing['date'].date()
start = '2014-01-01'
stop = '2022-12-31 '
pair_name = 'USD/SEK'
tenor = []

# for pair_name in df['pair_name'].unique():

if isinstance(start, str):
    start = datetime.strptime(start.strip(), "%Y-%m-%d").date()
if isinstance(stop, str):
    stop = datetime.strptime(stop.strip(), "%Y-%m-%d").date()
if isinstance(pair_name, str) and len(pair_name) == 7:
    # Warning missing tenor
    missing_tenor = df.loc[(df['pair_name'] == pair_name) & (df['earliest_date'].isnull()), 'tenor'].unique()
    if len(missing_tenor) > 0:
        print("Warning: The following tenor can not be found: ", missing_tenor)
    # Start Time Warnings
    early_list = df.loc[df['pair_name'] == pair_name, 'earliest_date'].unique()
    early_list = [x for x in early_list if x == x] #remove nan
    # Warning Multiple dates
    if len(early_list) > 1:
        print("Warning: Multiple start dates have been found for this pair.")
    # compare start with available data
    elif early_list[0].date() >= start:
        print("Time period not supported. Earliest available date: ", early_list[0])
        start = early_list[0].date()
    # End Time Warnings
    last_list = df.loc[df['pair_name'] == pair_name, 'latest_date'].unique()
    last_list = [x for x in last_list if x == x] #remove nan
    # Warning Multiple dates
    if len(last_list) > 1:
        print("Warning: Multiple end dates have been found for this pair.")
    # compare stop with available data
    elif last_list[0].date() < stop:
        print("Time period not supported. Latest available date: ", late_list[0])
        stop = late_list[0].date()



print(df_missing.loc[(df_missing['pair_name'] == pair_name) & (df_missing['date'] >= start) & (df_missing['date'] <= stop)][['date','tenor']])
        # print(start, stop)
    # except:
        # print(exception)





# df2.to_csv("../storage/csv/analysis/fxspot_missing_year_drilldown.csv", index=False)


# start = 45
# for i in range(40,start):
#     if i == 42:
#         continue
#
#     print(i)


# from sqlalchemy import create_engine, text
# from sqlalchemy.pool import NullPool
# from datetime import timedelta
# # from datetime import datetime
# pd.set_option('display.max_rows', None)
# pd.set_option('display.max_columns', None)
# pd.set_option('display.width', 2000)
# #
# engine = create_engine('postgresql+psycopg2://ryanhayashino:qwerty@localhost:5432/pangea_dump_5_21', poolclass=NullPool)
# start_query = start_query = """Select date,extract(dow from date) as dow from marketdata_fxspot
#             where pair_id= :pair
#             order by date ASC"""
#
# query = """Select distinct pair_id from marketdata_fxforward
# """
# pair = 46
# # # tenor =
# df = pd.read_sql_query(sql=text(start_query).bindparams(pair=pair), con=engine.connect())
# engine.connect().close()
# # # start = df['min'].iloc[0]
# print(df)
#
# if df.empty:
#     print('empty')
# elif start == None:
#
#     import pandas as pd
#     from sqlalchemy import create_engine, text
#     from datetime import timedelta
#     from datetime import datetime
#
#     engine = create_engine('postgresql+psycopg2://ryanhayashino:qwerty@localhost:5432/pangea_dump_5_21')
#     start_query = """Select min(date), max(date) from marketdata_fxforward
#                 where pair_id= :pair"""
#
#     query = """Select date, extract(dow from date) as dow, pair_id, tenor from marketdata_fxforward
#                 where pair_id= :pair and tenor = :tenor
#                 and date >= :start and date <= :stop
#                 order by date ASC"""
#     # start = '1986-01-02'
#     # stop = '2023-05-19'
#     all_pairs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
#                  31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 45,
#                  46, 47, 48, 49, 50, 51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
#                  72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93]
#     all_tenors = ['4Y', '7M', 'SW', '1Y', '10Y', 'SN', '18M', '6M', '5Y', '7Y', '6W', '1W', '5M', '10M', '3Y', '8M',
#                   '2Y', '11M', '1M', '15M', 'TN', '3M', '2M', '9M', '3W', '4M', '2W', 'ON', '1D']
#     test_pairs = 17
#     test_tenors = ['SN', '18M']
#
#     conn_counter = 0
#     # initiate empty list used to append rows to final df
#     data_missing = []
#     data_detail = []
#     day_delta = timedelta(days=1)
#     day_we_delta = timedelta(days=3)
#     # def get_bizday(start,stop):
#     for pair in all_pairs:
#         # query min/max dates per pair
#         date_df = pd.read_sql_query(sql=text(start_query).bindparams(pair=pair), con=engine.connect())
#         start = date_df['min'].iloc[0]
#         stop = date_df['max'].iloc[0]
#         if (date_df.empty) | (start is None and stop is None):
#             print("Pair Index Not found for: ", pair)
#             data_detail.append([None, pair, None])
#             continue
#         else:
#             for tenor in all_tenors:
#                 found_inx = []
#                 # collect earilest record date for pair/tenor
#                 data_detail.append([start, pair, tenor])
#                 if conn_counter >= 20:
#                     session.close()
#                     engine = create_engine(
#                         'postgresql+psycopg2://ryanhayashino:qwerty@localhost:5432/pangea_dump_5_21')
#                     print("refreshing session")
#                 # query fx_forward by pair/tenor/start/stop
#                 df = pd.read_sql_query(sql=text(query).bindparams(pair=pair, tenor=tenor, start=start, stop=stop),
#                                        con=engine.connect())
#                 conn_counter += 1
#                 if df.empty:
#                     data_detail.append([None, pair, tenor])
#                     print("Missing Data Pair: ", pair, " Tenor: ", tenor)
#                 else:
#                     # iterate with big windows looking for missing dates
#                     big_win = 15
#                     print(pair, " ", tenor)
#                     for big_window in df.rolling(window=big_win):
#                         dow_sum = big_window['dow'].sum()
#                         # look for instance of missing days of week, ignore windows without sufficient data
#                         if (dow_sum != (big_win * 3) and len(big_window) >= big_win):
#                             mini_win = 2
#                             # iterate with small windows when big window is suspicious
#                             for mini_window in big_window.rolling(window=mini_win):
#                                 # ignore values if they have already been accounted for
#                                 if mini_window.index[0] in found_inx:
#                                     continue
#                                 elif (len(mini_window) == mini_win):
#                                     dow_base = mini_window['dow'].iloc[0]
#                                     dow_lead = mini_window['dow'].iloc[1]
#                                     dow_delta = dow_lead - dow_base
#                                     if (dow_base == 5) & (dow_delta == -4):
#                                         continue
#                                     elif dow_delta == 1:
#                                         continue
#                                     else:
#                                         # print(mini_window) #remove after testing
#                                         if mini_window.index[0] not in found_inx:
#                                             found_inx.append(mini_window.index[0])
#                                         beg_date = mini_window['date'].iloc[0].date()
#                                         end_date = mini_window['date'].iloc[1].date()
#                                         count = 0
#                                         while beg_date != end_date:
#                                             count += 1
#                                             # print(beg_date) #remove after testing
#                                             # save missing dates, later added to missing_df
#                                             if count > 1:
#                                                 data_missing.append(
#                                                     [beg_date, int(beg_date.isoweekday()), pair, tenor])
#                                             # add 1 day or 3 days if weekend
#                                             if int(beg_date.isoweekday()) == 5:
#                                                 beg_date += day_we_delta
#                                             else:
#                                                 beg_date += day_delta
#                                 else:
#                                     pass
#                         else:
#                             pass
#
#     detail_df = pd.DataFrame(data_detail, columns=['earliest_date', "pair_id", "tenor"])
#     missing_df = pd.DataFrame(data_missing, columns=['date', 'dow', 'pair_id', 'tenor'])
#
#     detail_df.to_csv("../storage/csv/analysis/details_data_fxforward.csv")
#     missing_df.to_csv("../storage/csv/analysis/missing_data_fxforward.csv")
#
#     # result = [f(date, dow) for date, dow in zip(df['date'], df['dow'])]
#
# # [1,2, 3,4, 5, 6, 7, 8, 9, 10, 11,12, 13, 14,  15, 16, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,33,34,35,36,37,38,39,40,41, 42,45,46,47,48,49,50,51,52,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,
# # 83,84,85,86,87,88,89,90,91,92,93]
#
#
#
# import pandas as pd
# from sqlalchemy import create_engine, text
# from datetime import timedelta
# from datetime import datetime
#
# engine = create_engine('postgresql+psycopg2://ryanhayashino:qwerty@localhost:5432/pangea_dump_5_21')
# start_query = """Select min(date), max(date) from marketdata_fxforward
#             where pair_id= :pair"""
#
# query = """Select date, extract(dow from date) as dow, pair_id, tenor from marketdata_fxforward
#             where pair_id= :pair and tenor = :tenor
#             and date >= :start and date <= :stop
#             order by date ASC"""
# # start = '1986-01-02'
# # stop = '2023-05-19'
# all_pairs = [1,2,3,4,5, 6, 7, 8, 9, 10, 11,12, 13, 14, 15, 16, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,33,34,35,36,37,38,39,40,41,42,45,
#              46,47,48,49,50,51,52,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93]
# all_tenors = ['4Y', '7M', 'SW', '1Y', '10Y', 'SN', '18M', '6M', '5Y', '7Y', '6W', '1W', '5M', '10M', '3Y', '8M', '2Y', '11M', '1M', '15M', 'TN', '3M', '2M', '9M', '3W', '4M', '2W', 'ON', '1D']
# test_pairs = 17
# test_tenors = ['SN', '18M']
#
# conn_counter = 0
# # initiate empty list used to append rows to final df
# data_missing = []
# data_detail = []
# day_delta = timedelta(days=1)
# day_we_delta = timedelta(days=3)
# # def get_bizday(start,stop):
# for pair in all_pairs:
#     # query min/max dates per pair
#     date_df = pd.read_sql_query(sql=text(start_query).bindparams(pair=pair), con=engine.connect())
#     start = date_df['min'].iloc[0]
#     stop = date_df['max'].iloc[0]
#     if (date_df.empty) | (start is None and stop is None):
#         print("Pair Index Not found for: ", pair)
#         data_detail.append([None, pair, None])
#         continue
#     else:
#         for tenor in all_tenors:
#             found_inx = []
#             #collect earilest record date for pair/tenor
#             data_detail.append([start,pair,tenor])
#             # query fx_forward by pair/tenor/start/stop
#             df = pd.read_sql_query(sql=text(query).bindparams(pair=pair, tenor=tenor, start=start, stop=stop), con=engine.connect())
#             if df.empty:
#                 data_detail.append([None, pair, tenor])
#                 print("Missing Data Pair: ", pair, " Tenor: ", tenor)
#             else:
#                 # iterate with big windows looking for missing dates
#                 big_win = 15
#                 print(pair," ", tenor)
#                 for big_window in df.rolling(window=big_win):
#                     dow_sum = big_window['dow'].sum()
#                     # look for instance of missing days of week, ignore windows without sufficient data
#                     if (dow_sum != (big_win*3) and len(big_window) >= big_win):
#                         mini_win = 2
#                         # iterate with small windows when big window is suspicious
#                         for mini_window in big_window.rolling(window=mini_win):
#                             #ignore values if they have already been accounted for
#                             if mini_window.index[0] in found_inx:
#                                 continue
#                             elif (len(mini_window) == mini_win):
#                                 dow_base = mini_window['dow'].iloc[0]
#                                 dow_lead = mini_window['dow'].iloc[1]
#                                 dow_delta = dow_lead - dow_base
#                                 if (dow_base == 5) & (dow_delta == -4):
#                                     continue
#                                 elif dow_delta == 1:
#                                     continue
#                                 else:
#                                     # print(mini_window) #remove after testing
#                                     if mini_window.index[0] not in found_inx:
#                                         found_inx.append(mini_window.index[0])
#                                     beg_date = mini_window['date'].iloc[0].date()
#                                     end_date = mini_window['date'].iloc[1].date()
#                                     count = 0
#                                     while beg_date != end_date:
#                                         count += 1
#                                         # print(beg_date) #remove after testing
#                                         #save missing dates, later added to missing_df
#                                         if count > 1:
#                                             data_missing.append([beg_date, int(beg_date.isoweekday()), pair, tenor])
#                                         #add 1 day or 3 days if weekend
#                                         if int(beg_date.isoweekday()) == 5:
#                                             beg_date += day_we_delta
#                                         else:
#                                             beg_date += day_delta
#                             else:pass
#                     else:pass
#
# detail_df = pd.DataFrame(data_detail, columns = ['earliest_date', "pair_id", "tenor"])
# missing_df = pd.DataFrame(data_missing, columns = ['date', 'dow', 'pair_id', 'tenor'])
#
# detail_df.to_csv("../storage/csv/analysis/details_data_fxforward.csv")
# missing_df.to_csv("../storage/csv/analysis/missing_data_fxforward.csv")
#
#
#
#             # result = [f(date, dow) for date, dow in zip(df['date'], df['dow'])]
#
