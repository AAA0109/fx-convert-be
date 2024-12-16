import pandas as pd
from datetime import datetime
#display settings
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 2000)

# USER INPUT VARIABLES
start = '1980-01-01'  # format: string, eg. "yyyy-mm-dd"
stop = '2022-12-31'   # format: string, eg. "yyyy-mm-dd"
pair_name_list = ['USD/ZAR', 'USD/CHF', 'USD/SEK']   # format: list of strings, eg. ['XXX/XXX']
tenor_list = ['5M', '10M']    # format: list of strings, eg. ['XXX/XXX']


df = pd.read_csv("../storage/csv/analysis/fxforward_details_data.csv")
df['earliest_date'] = pd.to_datetime(df['earliest_date'], format = "%Y/%m/%d %H:%M:%S")
df['latest_date'] = pd.to_datetime(df['latest_date'], format = "%Y/%m/%d %H:%M:%S")
df_missing = pd.read_csv("../storage/csv/analysis/fxforward_missing_data.csv")
df_missing['date'] = pd.to_datetime(df_missing['date'], format = "%Y/%m/%d", utc=False).dt.date
temp_data_list = []
missing_data = []


for pair_name in pair_name_list:
    print("Checking availability for:", pair_name)
    if isinstance(start, str):
        start = datetime.strptime(start.strip(), "%Y-%m-%d").date()
    if isinstance(stop, str):
        stop = datetime.strptime(stop.strip(), "%Y-%m-%d").date()
    if isinstance(pair_name, str) and len(pair_name) == 7:
        # Warning missing tenor
        if len(tenor_list) > 0:
            missing_tenors = df.loc[(df['pair_name'] == pair_name) & (df['earliest_date'].isnull()) & (df['tenor'].isin(tenor_list)), 'tenor'].unique()
        else:
            missing_tenors = df.loc[(df['pair_name'] == pair_name) & (df['earliest_date'].isnull()), 'tenor'].unique()
        if len(missing_tenors) > 0:
            print("Warning: The following tenor can not be found: ", missing_tenors)
        # remove missing_tenors from tenor_list
        tenor_list = [x for x in tenor_list if x not in missing_tenors]

        # Start Time Warnings
        early_list = df.loc[df['pair_name'] == pair_name, 'earliest_date'].unique()
        early_list = [x for x in early_list if x == x] # remove nan
        # Warning Multiple dates
        if len(early_list) > 1:
            print("Warning: Multiple start dates have been found for this pair.")
        # compare start with available data
        elif early_list[0].date() >= start:
            print("Time period not supported for", pair_name, "Earliest available date: ", early_list[0])
            start = early_list[0].date()
        # End Time Warnings
        last_list = df.loc[df['pair_name'] == pair_name, 'latest_date'].unique()
        last_list = [x for x in last_list if x == x] #remove nan
        # Warning Multiple dates
        if len(last_list) > 1:
            print("Warning: Multiple end dates have been found for this pair.")
        # compare stop with available data
        elif last_list[0].date() < stop:
            print("Time period not supported. Latest available date: ", last_list[0])
            stop = last_list[0].date()

        if len(tenor_list) > 0:
            missing_subset = df_missing.loc[
                (df_missing['pair_name'] == pair_name) & (df_missing['tenor'].isin(tenor_list)) & (df_missing['date'] >= start) & (df_missing['date'] <= stop)][
                ['date', 'tenor', 'pair_name', 'pair_id', 'base_id', 'base_name', 'quote_id', 'quote_name']]
        else:
            missing_subset = df_missing.loc[(df_missing['pair_name'] == pair_name) & (df_missing['date'] >= start) & (df_missing['date'] <= stop)][['date','tenor','pair_name','pair_id','base_id','base_name','quote_id','quote_name']]
        #iterate through all dates, collecting pair_id, tenors that are missing data.
        if len(missing_subset) > 0:
            missing_date_count = 0
            for date in missing_subset['date'].unique():
                missing_date_count += 1
                missing_data.append([date, missing_subset[missing_subset['date'] == date]['tenor'].unique()
                                     ,pair_name, missing_subset['pair_id'].iloc[0]
                                     ,missing_subset['base_id'].iloc[0], missing_subset['base_name'].iloc[0]
                                     ,missing_subset['quote_id'].iloc[0], missing_subset['quote_name'].iloc[0]])
            print(missing_date_count, " Missing Dates for pair ", pair_name, '\n')
        else:
            print("No missing data for", pair_name, "within specified parameters.\n")


df_final = pd.DataFrame(missing_data, columns = ['date_missing','tenor_missing','pair_name','pair_id','base_id','base_name','quote_id','quote_name'])
df_final.to_csv("../storage/csv/analysis/fxforward_data_availability.csv", index=False)
