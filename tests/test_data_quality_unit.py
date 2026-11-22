
import pandas as pd
import pytest

from src.data_quality import validate_crime_data


@pytest.fixture
def valid_data():
    return pd.DataFrame(
        {
            "OBJECTID": [1, 2, 3],
            "REPORT_DATE": [
                "2026-09-01",
                "2026-09-15",
                "2026-09-30",
            ],
            "OFFENCE": [
                "Assault",
                "B&E",
                "Theft Of Motor Vehicle",
            ],
            "NEIGHBOURHOOD_158": [
                "Moss Park (73)",
                "Annex (95)",
                "Malvern East (146)",
            ],
            "LAT_WGS84": [
                43.65,
                43.67,
                43.81,
            ],
            "LONG_WGS84": [
                -79.37,
                -79.40,
                -79.22,
            ],
        }
    )


def test_valid_dataset_passes(valid_data):
    validate_crime_data(
        valid_data,
        year=2026,
        month=9,
    )


def test_empty_dataset_fails(valid_data):
    empty_data = valid_data.iloc[0:0]

    with pytest.raises(ValueError, match="empty"):
        validate_crime_data(empty_data)


def test_missing_column_fails(valid_data):
    invalid_data = valid_data.drop(
        columns=["OFFENCE"]
    )

    with pytest.raises(ValueError, match="Missing required"):
        validate_crime_data(invalid_data)


def test_duplicate_object_ids_fail(valid_data):
    invalid_data = valid_data.copy()
    invalid_data.loc[1, "OBJECTID"] = 1

    with pytest.raises(ValueError, match="Duplicate"):
        validate_crime_data(invalid_data)


def test_missing_object_ids_fail(valid_data):
    invalid_data = valid_data.copy()
    invalid_data.loc[1, "OBJECTID"] = None

    with pytest.raises(ValueError, match="Missing OBJECTID"):
        validate_crime_data(invalid_data)


def test_invalid_dates_fail(valid_data):
    invalid_data = valid_data.copy()
    invalid_data.loc[0, "REPORT_DATE"] = "invalid-date"

    with pytest.raises(ValueError, match="Invalid report dates"):
        validate_crime_data(invalid_data)


def test_wrong_year_fails(valid_data):
    invalid_data = valid_data.copy()
    invalid_data.loc[0, "REPORT_DATE"] = "2025-09-01"

    with pytest.raises(ValueError, match="outside 2026"):
        validate_crime_data(
            invalid_data,
            year=2026,
            month=9,
        )


def test_wrong_month_fails(valid_data):
    invalid_data = valid_data.copy()
    invalid_data.loc[0, "REPORT_DATE"] = "2026-08-31"

    with pytest.raises(ValueError, match="outside month 9"):
        validate_crime_data(
            invalid_data,
            year=2026,
            month=9,
        )


def test_all_missing_offences_fail(valid_data):
    invalid_data = valid_data.copy()
    invalid_data["OFFENCE"] = None

    with pytest.raises(ValueError, match="No offence categories"):
        validate_crime_data(invalid_data)


def test_some_missing_offences_allowed(valid_data):
    partially_missing = valid_data.copy()
    partially_missing.loc[0, "OFFENCE"] = None

    validate_crime_data(
        partially_missing,
        year=2026,
        month=9,
    )
