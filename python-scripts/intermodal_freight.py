import pandas as pd
import numpy as np
import math
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

file_path ="INPUT_FILE"

freight_data_raw = pd.read_csv(file_path)
additional_cols=['co2e','hub_equipment_co2e', 'vehicle_operation_co2e', 'vehicle_energy_provision_co2e', 'distance_km','notices','error']
freight_data_raw=freight_data_raw.reindex(columns=[*freight_data_raw.columns.tolist(), *additional_cols])

authorization_headers = {"Authorization": "Bearer API_KEY"}

url = "https://api.climatiq.io/freight/v2/intermodal"
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

## Make sure to rename the input columns
freight_data_raw=freight_data_raw.rename(columns={'START': 'start',
                            'DESTINATION': 'destination',
                            'MAIN_TYPE_OF_TRANSPORT': 'main_mode_of_transport',
                            'VEHICLE_TYPE': 'vehicle_type',
                            'WEIGHT': 'cargo_weight',
                            'WEIGHT_UNIT': 'cargo_weight_unit'})

freight_data_raw = freight_data_raw.replace(np.nan, '')

for i, row in freight_data_raw.iterrows():

    route = []
    cargo = { 'weight': row['cargo_weight'],
             'weight_unit': row['cargo_weight_unit'] }

    route.append({"location": {"query": row['start']}})

    if (row['vehicle_type']==''):
      main_leg = {"transport_mode": row['main_mode_of_transport']}
    else:
      mode = row['main_mode_of_transport']
      if mode == 'air':
        main_leg = {"transport_mode": row['main_mode_of_transport'],
                    "leg_details": {
                      "aircraft_type": row['vehicle_type']}}
      elif mode == 'sea':
        main_leg = {"transport_mode": row['main_mode_of_transport'],
                    "leg_details": {
                      "vessel_type": row['vehicle_type']}}
      elif mode == 'road':
        main_leg = {"transport_mode": row['main_mode_of_transport'],
                    "leg_details": {
                      "vehicle_type": row['vehicle_type']}}


    if (row['main_mode_of_transport'] == 'road'):
        route.append(main_leg)
    else:
      route.append({"transport_mode": 'road'})
      route.append(main_leg)
      route.append({"transport_mode": 'road'})


    route.append({"location": {"query": row['destination']}})

    json_object = {
        "route": route,
        "cargo": cargo
    }
    print (json_object)

    response = session.post(url, json=json_object, headers=authorization_headers)
    data = response.json()

    if (response.status_code != 200):
        freight_data_raw.at[i,'Error'] = data['message']
        continue
    freight_data_raw.at[i,'co2e'] = data['co2e']
    freight_data_raw.at[i,'hub_equipment_co2e'] = data['hub_equipment_co2e']
    freight_data_raw.at[i,'vehicle_operation_co2e'] = data['vehicle_operation_co2e']
    freight_data_raw.at[i,'vehicle_energy_provision_co2e'] = data['vehicle_energy_provision_co2e']
    freight_data_raw.at[i,'distance_km'] = data['distance_km']

    notices = ""
    if (len(data['notices']) > 0):
      for note in response["notices"]:
        notices = notices + note + ", "
    freight_data_raw.at[i,'notices'] = notices

# Extraction to flat file
freight_data_raw.to_csv('FreightEmissions.csv', index=False)








