
from pathlib import Path
from datetime import datetime, timezone


import pandas as pd
import requests

BASE_URL = (
    "https://services.arcgis.com/"
    "S9th0jAJ7bqgIRjw/ArcGIS/rest/services/"
    "Major_Crime_Indicators_Open_Data/FeatureServer/0/query"
)

BATCH_SIZE = 2000
MAX_RECORDS = 5000

OUTPUT_FILE = Path("data/raw/toronto_crime_recent.csv")


def download_crime_data():
    all_records = []
    offset = 0

    print("Starting SafeStreets data download...")

    with requests.Session() as session:
        while offset < MAX_RECORDS:
            batch_size = min(
                BATCH_SIZE,
                MAX_RECORDS - offset
            )

            response = session.get(
                BASE_URL,
                params={
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "false",
                    "orderByFields": "REPORT_DATE DESC, OBJECTID DESC",
                    "resultOffset": offset,
                    "resultRecordCount": batch_size,
                    "f": "json",
                },
                timeout=60,
            )

            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise RuntimeError(data["error"])

            records = [
                feature["attributes"]
                for feature in data.get("features", [])
            ]

            if not records:
                break

            all_records.extend(records)
            offset += len(records)

            print(
                f"Downloaded {len(all_records)} records"
            )

            if len(records) < batch_size:
                break

    if not all_records:
        raise RuntimeError("No records downloaded.")

    df = pd.DataFrame(all_records)

    if df["OBJECTID"].duplicated().any():
        raise RuntimeError(
            "Duplicate OBJECTID values found. "
            "Check pagination before continuing."
        )

    for column in ["REPORT_DATE", "OCC_DATE"]:
        df[column] = pd.to_datetime(
            df[column],
            unit="ms",
            utc=True,
            errors="coerce",
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(OUTPUT_FILE, index=False)


    timestamp_file = Path("data/processed/last_refresh.txt")

    timestamp_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp_file.write_text(
        datetime.now(timezone.utc).isoformat(),
        encoding="utf-8",
    )


    print("\nDownload complete!")
    print("Total records:", len(df))

    print("\nReport date range:")
    print("Earliest:", df["REPORT_DATE"].min())
    print("Latest:", df["REPORT_DATE"].max())

    print("\nUnique neighbourhoods:")
    print(df["NEIGHBOURHOOD_158"].nunique())

    print("\nTop five offences:")
    print(df["OFFENCE"].value_counts().head())

    print("\nSaved to:", OUTPUT_FILE)


if __name__ == "__main__":
    download_crime_data()
