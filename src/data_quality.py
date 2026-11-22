
import pandas as pd

REQUIRED_COLUMNS = [
    "OBJECTID",
    "REPORT_DATE",
    "OFFENCE",
    "NEIGHBOURHOOD_158",
    "LAT_WGS84",
    "LONG_WGS84",
]


def validate_crime_data(
    df: pd.DataFrame,
    year: int | None = None,
    month: int | None = None,
) -> None:
    if df.empty:
        raise ValueError("Dataset is empty.")

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if df["OBJECTID"].isna().any():
        raise ValueError("Missing OBJECTID values.")

    if df["OBJECTID"].duplicated().any():
        raise ValueError("Duplicate OBJECTIDs found.")

    dates = pd.to_datetime(
        df["REPORT_DATE"],
        utc=True,
        errors="coerce",
    )

    if dates.isna().any():
        raise ValueError("Invalid report dates found.")

    if year is not None:
        if not dates.dt.year.eq(year).all():
            raise ValueError(
                f"Records outside {year} found."
            )

    if month is not None:
        if not dates.dt.month.eq(month).all():
            raise ValueError(
                f"Records outside month {month} found."
            )

    if df["OFFENCE"].isna().all():
        raise ValueError("No offence categories found.")
