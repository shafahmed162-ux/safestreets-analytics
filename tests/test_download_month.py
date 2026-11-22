
from unittest.mock import Mock

import pandas as pd
import pytest

from src.download_month import download_month


def make_record(object_id, report_date=1780272000000):
    return {
        "OBJECTID": object_id,
        "REPORT_DATE": report_date,
        "OCC_DATE": report_date,
        "OFFENCE": "Assault",
        "NEIGHBOURHOOD_158": "Moss Park (73)",
        "LAT_WGS84": 43.65,
        "LONG_WGS84": -79.37,
    }


def test_rejects_invalid_month():
    with pytest.raises(ValueError, match="Month"):
        download_month(2026, 13)


def test_rejects_empty_pagination(monkeypatch):
    def fake_fetch(session, params):
        if params.get("returnCountOnly") == "true":
            return {"count": 2}

        return {"features": []}

    monkeypatch.setattr(
        "src.download_month.fetch_json",
        fake_fetch,
    )

    with pytest.raises(RuntimeError, match="empty batch"):
        download_month(2026, 9)


def test_rejects_source_count_changes(monkeypatch):
    count_calls = 0

    def fake_fetch(session, params):
        nonlocal count_calls

        if params.get("returnCountOnly") == "true":
            count_calls += 1
            return {"count": 1 if count_calls == 1 else 2}

        return {
            "features": [
                {"attributes": make_record(1)}
            ]
        }

    monkeypatch.setattr(
        "src.download_month.fetch_json",
        fake_fetch,
    )

    with pytest.raises(RuntimeError, match="count changed"):
        download_month(2026, 9)


def test_rejects_duplicate_records(monkeypatch):
    def fake_fetch(session, params):
        if params.get("returnCountOnly") == "true":
            return {"count": 2}

        return {
            "features": [
                {"attributes": make_record(1)},
                {"attributes": make_record(1)},
            ]
        }

    monkeypatch.setattr(
        "src.download_month.fetch_json",
        fake_fetch,
    )

    with pytest.raises(ValueError, match="Duplicate"):
        download_month(2026, 9)


def test_successful_download_saves_csv(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)

    september_date = int(
        pd.Timestamp(
            "2026-09-15",
            tz="UTC",
        ).timestamp() * 1000
    )

    def fake_fetch(session, params):
        if params.get("returnCountOnly") == "true":
            return {"count": 2}

        return {
            "features": [
                {
                    "attributes": make_record(
                        1,
                        september_date,
                    )
                },
                {
                    "attributes": make_record(
                        2,
                        september_date,
                    )
                },
            ]
        }

    monkeypatch.setattr(
        "src.download_month.fetch_json",
        fake_fetch,
    )

    download_month(2026, 9)

    output = (
        tmp_path
        / "data/raw/toronto_crime_2026_09.csv"
    )

    assert output.exists()

    saved = pd.read_csv(output)

    assert len(saved) == 2
    assert saved["OBJECTID"].is_unique
    assert saved["OFFENCE"].notna().all()

