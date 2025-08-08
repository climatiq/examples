import pandas as pd
import numpy as np
import requests
import time
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
file_path = "AP_script_sample_data.xlsx" # Input data file name
output_path = "AP_script_output.xlsx" # Desired name of the final output file to be called
max_suggestions = 5 # Adjust this to as many matcches per item as required
api_key = "REPLACE_WITH_YOUR_KEY"  # Replace with your API key
authorization_headers = {"Authorization": f"Bearer {api_key}"} # Set Authorisation headers with API key
url = "https://preview.api.climatiq.io/autopilot/v1-preview4/suggest" # URL of the Autopilot Suggest endpoint that the POST request is sent to.

# Setup session with retry logic
session = requests.Session()
retries = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)

# Load and clean data
# Read and rename input columns to match expected API schema. The columns in your file need to have the same names as the capitalized names below.
# For example, your procured items column name needs to be "TEXT", unit type needs to be re-named to "UNIT_TYPE" and so forth.
# Alternatively, you can change the capitalized column names in the code below to match your existing column header names.
input_df = pd.read_excel(file_path)
input_df = input_df.rename(columns={
    'TEXT': 'text', # Required field
    'MODEL': 'model', # Optional, delete if not used
    'UNIT_TYPE': 'unit_type', # Optional, but can be Weight, Spend, Volume or Number, one or multiple possible
    'YEAR': 'year', # Optional, delete if not used
    'REGION': 'region', # Optional, delete if not used
    'REGION_FALLBACK': 'region_fallback', # Optional, delete if not used
    'SOURCE': 'source', # Optional, delete if not used
    'EXCLUDE_SOURCE': 'exclude_source', # Optional, delete if not used
    'LCA_ACTIVITY': 'source_lca_activity' # Optional, delete if not used
})
input_df = input_df.replace(np.nan, '')

# Define output columns
base_cols = ['suggestion_name', 'sector', 'category', 'unit_type', 'source', 'year_relevant', 'year_released',
             'region_name',  'source_lca_activity', 'data_quality_flag']
output_cols = [f"{col}_{i+1}" for i in range(max_suggestions) for col in base_cols]
for col in output_cols:
    input_df[col] = ""

# Optional fields to check for
optional_fields = [
    "model", "unit_type", "year", "region", "region_fallback",
    "source", "exclude_source", "source_lca_activity"
]

# Loop over each row
for idx, row in input_df.iterrows():
    text = str(row.get("text", "")).strip()

    if not text:
        for col in output_cols:
            input_df.at[idx, col] = "MISSING_REQUIRED_FIELDS"
        continue

    # Construct payload
    suggest_payload = {
        "suggest": {
            "text": text
        },
        "max_suggestions": max_suggestions
    }

    # Add optional fields with correct types and structure
    for field in optional_fields:
        value = row.get(field, "")
        if str(value).strip() == "":
            continue

        clean_value = str(value).strip()

        if field == "year":
            try:
                suggest_payload["suggest"][field] = int(clean_value)
            except ValueError:
                continue

        elif field == "region_fallback":
            suggest_payload["suggest"][field] = clean_value.lower() == "true"

        elif field in ["unit_type", "source", "exclude_source", "source_lca_activity"]:
            # Ensure mutually exclusive for source/exclude_source
            if field == "exclude_source" and "source" in suggest_payload["suggest"]:
                continue
            if field == "source" and "exclude_source" in suggest_payload["suggest"]:
                continue

            values_array = [v.strip() for v in clean_value.split(",") if v.strip()]
            if values_array:
                suggest_payload["suggest"][field] = values_array

        else:
            suggest_payload["suggest"][field] = clean_value

    # Print payload for debugging
    print(f"\nPayload for row {idx}:\n" + json.dumps(suggest_payload, indent=2))

    # Make API request
    try:
        response = session.post(url, headers=authorization_headers, json=suggest_payload)
        response.raise_for_status()
        results = response.json().get("results", [])
    except requests.exceptions.HTTPError as e:
        print(f"\nAPI Error at row {idx}: {e}")
        print(f"Status Code: {response.status_code}")
        print("Response Body:", response.text)

        try:
            error_data = response.json()
            error_code = error_data.get("error_code", "")
            if error_code == "no_emission_factors_found":
                for col in output_cols:
                    input_df.at[idx, col] = "NO_MATCH_FOUND"
            else:
                for col in output_cols:
                    input_df.at[idx, col] = "API_ERROR"
        except Exception:
            for col in output_cols:
                input_df.at[idx, col] = "API_ERROR"
                continue
    except Exception as e:
        print(f"\nUnexpected error at row {idx}: {e}")
        for col in output_cols:
            input_df.at[idx, col] = "ERROR"
        continue

    # Fill suggestions into output columns
    for i, suggestion in enumerate(results[:max_suggestions]):
        ef = suggestion.get("emission_factor", {})
        flags = ef.get("data_quality_flags", [])
        data = {
            "suggestion_name": ef.get("name", ""),
            "sector": ef.get("sector", ""),
            "category": ef.get("category", ""),
            "unit_type": ef.get("unit_type", ""),
            "source": ef.get("source", ""),
            "year_relevant": ef.get("year", ""),
            "year_released": ef.get("year_released", ""),
            "region_name": ef.get("region_name", ""),
            "source_lca_activity": ef.get("source_lca_activity", ""),
            "data_quality_flag": "TRUE" if flags else "FALSE",
            "suggestion_details": suggestion.get("suggestion_details", "").get("label", "")
        }

        for key, val in data.items():
            input_df.at[idx, f"{key}_{i+1}"] = val

    time.sleep(0.2)

# Save to output Excel file
input_df.to_excel(output_path, index=False)
print(f"\nOutput saved to: {output_path}")
