import requests

BASE_URL = (
    "https://services.arcgis.com/"
    "S9th0jAJ7bqgIRjw/ArcGIS/rest/services/"
    "Major_Crime_Indicators_Open_Data/FeatureServer/0/query"
)

params = {
    "where": (
        "REPORT_DATE >= TIMESTAMP '2026-09-01 00:00:00' "
        "AND REPORT_DATE < TIMESTAMP '2026-10-01 00:00:00'"
    ),
    "returnCountOnly": "true",
    "f": "json",
}

response = requests.get(BASE_URL, params=params, timeout=60)
response.raise_for_status()

data = response.json()

if "error" in data:
  raise RuntimeError(data["error"])

print("SAFESTREETS — SEPTEMBER 2026")
print("----------------------------")
print("Available records:", data["count"])

