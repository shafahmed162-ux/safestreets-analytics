
from pathlib import Path

import pandas as pd

INPUT_FILE = Path("data/raw/toronto_crime_recent.csv")


def main():
    df = pd.read_csv(INPUT_FILE)

    print("SAFESTREETS — NEIGHBOURHOOD ANALYSIS")
    print("-----------------------------------")

    print(f"\nTotal records: {len(df):,}")

    print("\nMissing neighbourhood values:")
    print(df["NEIGHBOURHOOD_158"].isna().sum())

    print("\nTop 10 neighbourhood values by record count:")
    neighbourhood_counts = (
        df["NEIGHBOURHOOD_158"]
        .value_counts(dropna=False)
        .head(10)
    )

    print(neighbourhood_counts)

    print("\nNeighbourhood values requiring inspection:")
    unusual = df[
        df["NEIGHBOURHOOD_158"].astype("string").str.contains(
            "unknown|not assigned|outside|na",
            case=False,
            regex=True,
            na=False,
        )
    ]

    print(
        unusual["NEIGHBOURHOOD_158"]
        .value_counts()
        .head(10)
    )

    selected_neighbourhood = "Malvern East (146)"

    area_data = df[
        df["NEIGHBOURHOOD_158"]
        == selected_neighbourhood
    ]

    print(f"\nSELECTED AREA: {selected_neighbourhood}")
    print(f"Records in sample: {len(area_data)}")

    print("\nTop offences in selected area:")
    print(area_data["OFFENCE"].value_counts().head(10))

    if not area_data.empty:
        area_data = area_data.copy()

        area_data["REPORT_DATE"] = pd.to_datetime(
            area_data["REPORT_DATE"],
            utc=True,
            errors="coerce",
        )

        daily_counts = (
            area_data.groupby(
                area_data["REPORT_DATE"].dt.date
            )
            .size()
            .sort_index()
        )

        print("\nDaily reported-record counts:")
        print(daily_counts.tail(10))


if __name__ == "__main__":
    main()
