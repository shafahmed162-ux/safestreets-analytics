from pathlib import Path

import pandas as pd
import requests

BASE_URL = (
    "https://services.arcgis.com/"
    "S9th0jAJ7bqgIRjw/ArcGIS/rest/services/"
    "Major_Crime_Indicators_Open_Data/FeatureServer/0"
)

OUTPUT_FILE = Path("data/raw/toronto_crime_sample.csv")


def main():
    print("Fetching recent Toronto crime records...")

    response = requests.get(
        f"{BASE_URL}/query",
        params={
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "false",
            "orderByFields": "REPORT_DATE DESC, OBJECTID DESC",
            "resultRecordCount": 100,
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
        print("No records returned.")
        return

    df = pd.DataFrame(records)

    for column in ["REPORT_DATE", "OCC_DATE"]:
        if column in df.columns:
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

    print(f"\nRecords downloaded: {len(df)}")
    print(f"Columns available: {len(df.columns)}")

    print("\nReport date range:")
    print(df["REPORT_DATE"].min())
    print(df["REPORT_DATE"].max())

    print("\nTop reported offences:")
    print(df["OFFENCE"].value_counts().head(10))

    print("\nSample records:")
    print(
        df[
            [
                "REPORT_DATE",
                "OFFENCE",
                "NEIGHBOURHOOD_158",
            ]
        ].head()
    )

    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
