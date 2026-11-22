
import argparse
import calendar
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from src.data_quality import validate_crime_data

BASE_URL = (
    "https://services.arcgis.com/"
    "S9th0jAJ7bqgIRjw/ArcGIS/rest/services/"
    "Major_Crime_Indicators_Open_Data/FeatureServer/0/query"
)

BATCH_SIZE = 2000


def fetch_json(session, params):
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


def download_month(year, month):
    if not 1 <= month <= 12:
        raise ValueError("Month must be between 1 and 12.")

    start_date = f"{year}-{month:02d}-01"

    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    date_filter = (
        f"REPORT_DATE >= TIMESTAMP '{start_date} 00:00:00' "
        f"AND REPORT_DATE < TIMESTAMP '{end_date} 00:00:00'"
    )

    output_file = Path(
        f"data/raw/toronto_crime_{year}_{month:02d}.csv"
    )

    print("SAFESTREETS — MONTHLY DATA PIPELINE")
    print("-----------------------------------")
    print(
        f"Reporting period: "
        f"{calendar.month_name[month]} {year}"
    )

    records = []

    with requests.Session() as session:
        count_data = fetch_json(
            session,
            {
                "where": date_filter,
                "returnCountOnly": "true",
                "f": "json",
            },
        )

        expected_count = count_data["count"]
        print(f"Expected records: {expected_count:,}")

        if expected_count == 0:
            print("No records published for this month.")
            return

        offset = 0

        while offset < expected_count:
            batch_size = min(
                BATCH_SIZE,
                expected_count - offset,
            )

            data = fetch_json(
                session,
                {
                    "where": date_filter,
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
                    "API returned an empty batch."
                )

            records.extend(batch)
            offset += len(batch)

            print(f"Downloaded {offset:,} records")

        final_count = fetch_json(
            session,
            {
                "where": date_filter,
                "returnCountOnly": "true",
                "f": "json",
            },
        )["count"]

    if final_count != expected_count:
        raise RuntimeError(
            "Source record count changed during download. "
            "Please retry."
        )

    df = pd.DataFrame(records)

    if len(df) != expected_count:
        raise RuntimeError(
            "Downloaded record count does not match "
            "the source count."
        )

    for column in ["REPORT_DATE", "OCC_DATE"]:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                unit="ms",
                utc=True,
                errors="coerce",
            )

    validate_crime_data(
        df,
        year=year,
        month=month,
    )

    print("Data-quality validation passed.")

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = output_file.with_suffix(".tmp")
    df.to_csv(temp_file, index=False)
    temp_file.replace(output_file)

    print("\nDOWNLOAD SUCCESSFUL")
    print(f"Records: {len(df):,}")
    print(f"Saved to: {output_file}")
    print(
        "Completed at:",
        datetime.now(timezone.utc).isoformat(),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--year",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--month",
        type=int,
        required=True,
    )

    args = parser.parse_args()

    download_month(args.year, args.month)
