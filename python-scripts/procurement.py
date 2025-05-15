import pandas as pd
import numpy as np
import math
from datetime import datetime
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# If you are running this script in Google Colab, you can upload the file under the folder icon in the navigation bar on the left side
file_path ="INPUT_FILE_PATH"

procurement_data_raw = pd.read_csv(file_path)

# Make sure to set your API key here
api_key="API_KEY"
authorization_headers = {"Authorization": f"Bearer {api_key}"}

url = "https://api.climatiq.io/procurement/v1/spend/batch"
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# To make sure the following code knows which columns to use as input, we need to rename the columns of your data. Please replace the placeholders with the columns names as defined in your input data.
# Ensure that the currency has the following format: eur, usd, gbp, etc.
# Ensure that the spend region uses ISO codes: DE, GB, US, ...

input_table = procurement_data_raw
input_table=input_table.rename(columns={'SPEND_AMOUNT': 'money',
                            'MAPPED_ACTIVITY': 'activity_id',
                            'SPEND_YEAR': 'spend_year',
                            'CURRENCY': 'money_unit',
                            'SPEND_REGION': 'spend_region'})
input_table['money_unit'] = input_table['money_unit'].str.lower()
input_table['money'] = input_table['money'].apply(float)

# You can either use industry classification codes (NACE, UNSPSC or MCC) for the identification of the right emission factor or the activity_id. 
# Depening on your approach, run one of the following two codes:

#Run this is you have mapped your spend against EXIOBASE actvities - Please replace the placeholders with the columns names as defined in your input data
input_table=input_table.rename(columns={ 'MAPPED_ACTIVITY': 'activity_id'})

#Run this is you have mapped your spend against industry codes - make sure to replace the placeholders
input_table['classification_type'] = 'USED_SCHEME' #unspsc, nace2 or mcc
input_table=input_table.rename(columns={ 'INDUSTRY_CODE': 'classification_code'})

# Currency Check:
# Climatiq supports many different currencies, but we still need to check that your data does not contain any currencies not support by the API and if so, 
# ensure we apply a conversion factor to the data.

list_of_available_currencies = ["usd","afn","dzd","ars","aud","bhd","brl","cad","kyd","cny","dkk","egp","eur","hkd","huf","isk","inr","iqd","ils","jpy","lbp","mxn","mad","nzd","nok","qar","rub","sar","sgd","zar","krw","sek","chf","thb","twd","tnd","try","aed","gbp"]
used_currencies = procurement_data_raw["Currency"]
used_currencies = used_currencies.drop_duplicates().str.lower().reset_index()["Currency"].values.tolist()
currencies_to_be_converted = list(set(used_currencies) - set(list_of_available_currencies))

#List of currencies to be converted.
currencies_to_be_converted

# If the array above is empty, you can skip the remaining steps for the currency check.
# If these are currencies show, please make sure to enter the conversion rates to EUR into the array below.

conversions = pd.DataFrame({"factor" :[CONVERSION_RATE_1,CONVERSION_RATE_2,CONVERSION_RATE_3,...]}, index = currencies_to_be_converted)
conversions

#Applying the conversions
for index, row in conversions.iterrows():
    input_table.loc[input_table.money_unit==index,'money']*=row['factor']
    input_table.loc[input_table['money_unit'] == index, 'money_unit'] = 'eur'


# Calling the API in batches

results = pd.DataFrame()
for i in range(0, input_table.size, 100):

    subset = input_table.iloc[i:i + 100]

    if 'classification_type' in input_table.columns:
      json_data = subset.apply(lambda row: {
          'money': row['money'],
          'spend_region': row['spend_region'],
          'spend_year': row['spend_year'],
          'money_unit': row['money_unit'],
          'activity': {
              'classification_type': row['classification_type'],
              'classification_code': row['classification_code']
          }
      }, axis=1).to_json(orient='records')
    else:
      json_data = subset.apply(lambda row: {
          'money': row['money'],
          'spend_region': row['spend_region'],
          'spend_year': row['spend_year'],
          'money_unit': row['money_unit'],
          'activity': {
              'activity_id': row['activity_id']
          }
      }, axis=1).to_json(orient='records')
    jsonFormat = json.loads(json_data)
    response = session.post(url, json=jsonFormat, headers=authorization_headers)
    data = response.json()
    data = pd.json_normalize(data['results'])
    results = pd.concat([results, data], axis=0)

results

# Exporting the results
# Adjust the file path and name if needed. The file will show up on the left-hand side in the file explorer and can simply be downloaded to your machine.

results = results.reset_index(drop=True)
procurement_results = pd.concat([procurement_data_raw, results], axis=1)
procurement_results.to_csv('ProcurementEmissions.csv', index=False)

















