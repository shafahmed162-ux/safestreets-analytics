
from pathlib import Path

import pandas as pd
import requests

BASE_URL = (
    "https://services.arcgis.com/"
    "S9th0jAJ7bqgIRjw/ArcGIS/rest/services/"
    "Major_Crime_Indicators_Open_Data/FeatureServer/0/query"
)

DATE_FILTER = (
    "REPORT_DATE >= TIMESTAMP '2026-09-01 00:00:00' "
    "AND REPORT_DATE < TIMESTAMP '2026-10-01 00:00:00'"
)

BATCH_SIZE = 2000
OUTPUT_FILE = Path("data/raw/toronto_crime_september_2026.csv")


def request_data(session, params):
    response = session.get(
        BASE_URL,
        params=params,
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(data["error"])

    return data


def main():
    print("SAFESTREETS — SEPTEMBER DATA DOWNLOAD")
    print("------------------------------------")

    records = []
    offset = 0

    with requests.Session() as session:
        count_data = request_data(
            session,
            {
                "where": DATE_FILTER,
                "returnCountOnly": "true",
                "f": "json",
            },
        )

        expected_count = count_data["count"]
        print(f"Expected records: {expected_count:,}")

        while offset < expected_count:
            batch_size = min(
                BATCH_SIZE,
                expected_count - offset,
            )

            data = request_data(
                session,
                {
                    "where": DATE_FILTER,
                    "outFields": "*",
                    "returnGeometry": "false",
                    "orderByFields": "OBJECTID ASC",
                    "resultOffset": offset,
                    "resultRecordCount": batch_size,
                    "f": "json",
                },
            )

            batch = [
                feature["attributes"]
                for feature in data.get("features", [])
            ]

            if not batch:
                raise RuntimeError(
                    "The API returned an empty batch."
                )

            records.extend(batch)
            offset += len(batch)

            print(f"Downloaded: {len(records):,} records")

    df = pd.DataFrame(records)

    if len(df) != expected_count:
        raise RuntimeError(
            f"Record count mismatch: expected {expected_count}, "
            f"received {len(df)}."
        )

    if df["OBJECTID"].isna().any():
        raise RuntimeError("Some records have missing OBJECTIDs.")

    if df["OBJECTID"].duplicated().any():
        raise RuntimeError("Duplicate OBJECTIDs detected.")

    for column in ["REPORT_DATE", "OCC_DATE"]:
        df[column] = pd.to_datetime(
            df[column],
            unit="ms",
            utc=True,
            errors="coerce",
        )

    if df["REPORT_DATE"].isna().any():
        raise RuntimeError("Invalid report dates detected.")

    if not df["REPORT_DATE"].dt.year.eq(2026).all():
        raise RuntimeError("Records from unexpected years found.")

    if not df["REPORT_DATE"].dt.month.eq(9).all():
        raise RuntimeError("Records outside September found.")

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = OUTPUT_FILE.with_suffix(".tmp")
    df.to_csv(temp_file, index=False)
    temp_file.replace(OUTPUT_FILE)

    print("\nDOWNLOAD SUCCESSFUL")
    print("-------------------")
    print(f"Total records: {len(df):,}")
    print(f"Unique OBJECTIDs: {df['OBJECTID'].nunique():,}")

    print("\nReport date range:")
    print("Earliest:", df["REPORT_DATE"].min())
    print("Latest:", df["REPORT_DATE"].max())

    print("\nUnique neighbourhood labels:")
    print(df["NEIGHBOURHOOD_158"].nunique())

    print("\nTop 5 reported offences:")
    print(df["OFFENCE"].value_counts().head())

    print("\nSaved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
