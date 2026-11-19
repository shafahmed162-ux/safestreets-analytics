
import requests

BASE_URL = (
    "https://services.arcgis.com/"
    "S9th0jAJ7bqgIRjw/ArcGIS/rest/services/"
    "Major_Crime_Indicators_Open_Data/FeatureServer/0"
)

def main():
    response = requests.get(
        f"{BASE_URL}/query",
        params={
            "where": "1=1",
            "returnCountOnly": "true",
            "f": "json",
        },
        timeout=60,
    )

    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(data["error"])

    print("SafeStreets Dataset Information")
    print("------------------------------")
    print("Total records:", data.get("count"))

    response = requests.get(
        BASE_URL,
        params={"f": "json"},
        timeout=30,
    )
    response.raise_for_status()

    metadata = response.json()

    if "error" in metadata:
        raise RuntimeError(metadata["error"])

    print("Dataset:", metadata.get("name"))
    print(
        "Maximum records per request:",
        metadata.get("maxRecordCount"),
    )
    print(
        "Supports pagination:",
        metadata.get(
            "advancedQueryCapabilities", {}
        ).get("supportsPagination"),
    )

if __name__ == "__main__":
    main()
