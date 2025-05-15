import pandas as pd
import numpy as np
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Definition the API call method - __make sure to set your API key here!__
api_key="API Key"
authorization_headers = {"Authorization": f"Bearer {api_key}"}

url = "https://api.climatiq.io/data/v1/search"
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)


# Definition of filter
# Define which emission factors should be extracted.
# You can use the Data Explorer to understand which filters you might want to set.
# This is just an example, please make sure to define any filters in the Json object below
example_filter = {
    "data_version" : "^5",
    "query" : "Truck",
    "activity_id" : "",
    "category" : "Transport",
    "sector" : "Road Freight",
    "region" : "DE,GB,FR,US",
    "source" : "EPA",
    "year" : "",
    "unit_type" : "Money",
}

# Define your filters here, you can add multiple options per filter criteria by seperating them with a comma
filters = {
    "data_version" : "^21",
    "query" :"",
    "activity_id" : "",
    "category" : "",
    "sector" : "",
    "region" : "",
    "source" : "",
    "year" : "",
    "unit_type" : "",
}

# Construction of the search query
query = "?results_per_page=500"
for attribute, value in filters.items():
    if (value != ""):
        query = query + "&" + attribute + "=" + value

no_of_pages = 1
current_page = 1
results = pd.DataFrame()

while current_page <= no_of_pages:
    response = session.get(url+query+"&page="+str(current_page), headers=authorization_headers)
    data = response.json()
    current_page = current_page+1
    no_of_pages = data["last_page"]

    query_results = pd.DataFrame.from_records(data["results"])
    results = pd.concat([results, query_results])

## Extraction to flat file
# Adjust the file path and name if needed. You'll find the resulting file in the file explorer on the left hand side.
results.to_csv('Climatiq_Emission_Factor_Database.csv', index=False)

shortened_results = results[['activity_id', 'name', 'category', 'sector', 'source', 'unit_type']].drop_duplicates()
final = shortened_results.groupby(['activity_id', 'name', 'category', 'sector'])['source'].apply(','.join).reset_index()
final ["unit_type"] = shortened_results.groupby(['activity_id', 'name', 'category', 'sector'])['unit_type'].apply(','.join).reset_index()['unit_type']


final.to_csv('Climatiq_Emission_Factor_Database_GroupedByActivityIDs.csv', index=False)













