
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.download_crime_data import download_crime_data


DATASETS = {
    "Recent 5,000-record sample": Path(
        "data/raw/toronto_crime_recent.csv"
    ),
    "September 2026 — Complete month": Path(
        "data/raw/toronto_crime_september_2026.csv"
    ),
}

REFRESH_FILE = Path("data/processed/last_refresh.txt")


st.set_page_config(
    page_title="SafeStreets | Toronto Crime Analytics",
    page_icon="🛡️",
    layout="wide",
)


@st.cache_data
def load_data(file_path: str, modified_time: int):
    path = Path(file_path)

    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)

    df["REPORT_DATE"] = pd.to_datetime(
        df["REPORT_DATE"],
        utc=True,
        errors="coerce",
    )

    return df


st.title("🛡️ SafeStreets")

st.subheader(
    "Toronto Crime Analytics & Public Safety Intelligence"
)

st.caption(
    "Explore publicly available reported crime data from "
    "Toronto Police Service. Records reflect the latest "
    "available publication, not real-time police activity."
)


with st.sidebar:
    st.header("Explore Crime Data")

    selected_dataset = st.selectbox(
        "Dataset",
        options=list(DATASETS.keys()),
        index=1,
    )


DATA_FILE = DATASETS[selected_dataset]

st.divider()

refresh_col, status_col = st.columns([1, 3])

with refresh_col:
    refresh_clicked = st.button(
        "🔄 Refresh Recent Sample",
        use_container_width=True,
        disabled=(
            selected_dataset
            != "Recent 5,000-record sample"
        ),
    )

with status_col:
    if (
        selected_dataset
        == "Recent 5,000-record sample"
    ):
        st.caption(
            "Downloads the latest 5,000 records currently "
            "published by Toronto Police."
        )
    else:
        st.caption(
            "September 2026 is a saved complete-month snapshot. "
            "The recent-sample refresh button is disabled."
        )


if refresh_clicked:
    try:
        with st.spinner(
            "Downloading the latest published records..."
        ):
            download_crime_data()
            load_data.clear()

        st.rerun()

    except Exception as error:
        st.error(f"Data refresh failed: {error}")


if REFRESH_FILE.exists():
    last_refresh = pd.to_datetime(
        REFRESH_FILE.read_text(
            encoding="utf-8"
        ).strip(),
        utc=True,
        errors="coerce",
    )

    if pd.notna(last_refresh):
        st.caption(
            "Last successful recent-sample refresh: "
            f"{last_refresh:%B %d, %Y at %H:%M UTC}"
        )
    else:
        st.caption(
            "Last successful recent-sample refresh: Unknown"
        )
else:
    st.caption(
        "Last successful recent-sample refresh: "
        "Not recorded yet"
    )


if not DATA_FILE.exists():
    st.error(
        f"Dataset file not found: {DATA_FILE}. "
        "Run the appropriate downloader first."
    )
    st.stop()


df = load_data(
    str(DATA_FILE),
    DATA_FILE.stat().st_mtime_ns,
)

if df.empty:
    st.error(
        "The selected dataset is empty. "
        "Please download the data again."
    )
    st.stop()


df = df.dropna(subset=["REPORT_DATE"]).copy()

if df.empty:
    st.error("No valid report dates were found.")
    st.stop()


earliest_date = df["REPORT_DATE"].min()
latest_date = df["REPORT_DATE"].max()

is_complete_month = (
    selected_dataset
    == "September 2026 — Complete month"
)

if is_complete_month:
    st.info(
        f"Dataset: September 2026 reporting-month snapshot. "
        f"Records: {len(df):,}. "
        f"Report dates: "
        f"{earliest_date:%B %d, %Y} – "
        f"{latest_date:%B %d, %Y}. "
        "Published records may be revised."
    )
else:
    st.info(
        f"Dataset: Recent 5,000-record development sample. "
        f"Report dates: "
        f"{earliest_date:%B %d, %Y} – "
        f"{latest_date:%B %d, %Y}. "
        "The earliest day may be incomplete."
    )


neighbourhoods = sorted(
    df.loc[
        df["NEIGHBOURHOOD_158"].notna()
        & (df["NEIGHBOURHOOD_158"] != "NSA"),
        "NEIGHBOURHOOD_158",
    ]
    .unique()
    .tolist()
)


with st.sidebar:
    selected_area = st.selectbox(
        "Neighbourhood",
        options=["All neighbourhoods"] + neighbourhoods,
    )

    categories = sorted(
        df["OFFENCE"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_categories = st.multiselect(
        "Offence categories",
        options=categories,
        default=[],
        placeholder="All offence categories",
    )

    selected_dates = st.date_input(
        "Report date range",
        value=(
            earliest_date.date(),
            latest_date.date(),
        ),
        min_value=earliest_date.date(),
        max_value=latest_date.date(),
    )


if (
    not isinstance(selected_dates, (tuple, list))
    or len(selected_dates) != 2
):
    st.warning(
        "Please select both a start date and an end date."
    )
    st.stop()


start_date, end_date = selected_dates

filtered = df.copy()

if selected_area != "All neighbourhoods":
    filtered = filtered[
        filtered["NEIGHBOURHOOD_158"]
        == selected_area
    ]

if selected_categories:
    filtered = filtered[
        filtered["OFFENCE"].isin(selected_categories)
    ]

filtered = filtered[
    filtered["REPORT_DATE"].dt.date.between(
        start_date,
        end_date,
    )
]


col1, col2, col3 = st.columns(3)

col1.metric(
    "Reported records",
    f"{len(filtered):,}",
)

col2.metric(
    "Neighbourhoods represented",
    filtered.loc[
        filtered["NEIGHBOURHOOD_158"] != "NSA",
        "NEIGHBOURHOOD_158",
    ].nunique(),
)

col3.metric(
    "Offence categories",
    filtered["OFFENCE"].nunique(),
)


st.divider()

if filtered.empty:
    st.warning(
        "No records match the selected filters. "
        "Try adjusting the date range, neighbourhood, "
        "or offence categories."
    )
    st.stop()


left, right = st.columns(2)

with left:
    st.subheader("Most Common Reported Offences")

    offence_counts = (
        filtered["OFFENCE"]
        .value_counts()
        .head(10)
        .rename_axis("Offence")
        .reset_index(name="Records")
    )

    offence_chart = px.bar(
        offence_counts,
        x="Records",
        y="Offence",
        orientation="h",
        title="Top 10 Reported Offences",
    )

    offence_chart.update_layout(
        yaxis={
            "categoryorder": "total ascending"
        }
    )

    st.plotly_chart(
        offence_chart,
        use_container_width=True,
    )


with right:
    st.subheader("Reported Crime Over Time")

    daily_counts = (
        filtered.groupby(
            filtered["REPORT_DATE"].dt.date
        )
        .size()
        .rename_axis("Date")
        .reset_index(name="Records")
    )

    trend_chart = px.line(
        daily_counts,
        x="Date",
        y="Records",
        markers=True,
        title="Daily Reported Records",
    )

    st.plotly_chart(
        trend_chart,
        use_container_width=True,
    )


st.divider()

st.subheader("Explore Records")

display_columns = [
    "REPORT_DATE",
    "OFFENCE",
    "CSI_CATEGORY",
    "NEIGHBOURHOOD_158",
    "DIVISION",
]

st.dataframe(
    filtered[display_columns].sort_values(
        "REPORT_DATE",
        ascending=False,
    ),
    use_container_width=True,
    hide_index=True,
)


st.caption(
    "Source: Toronto Police Service public crime data. "
    "Published records may be preliminary, and geographic "
    "coordinates may be offset for privacy. "
    "Counts represent records, not population-adjusted "
    "crime rates or neighbourhood safety rankings."
)


st.divider()

st.header("Neighbourhood Comparison")

st.caption(
    "Compare reported offence records across two neighbourhoods "
    "using the selected dataset, date range, and offence filters. "
    "These counts are not adjusted for population."
)

compare_col1, compare_col2 = st.columns(2)

with compare_col1:
    area_a = st.selectbox(
        "First neighbourhood",
        neighbourhoods,
        key="compare_area_a",
    )

with compare_col2:
    area_b = st.selectbox(
        "Second neighbourhood",
        neighbourhoods,
        index=1 if len(neighbourhoods) > 1 else 0,
        key="compare_area_b",
    )

if area_a == area_b:
    st.warning("Please select two different neighbourhoods.")
else:
    comparison_data = df[
        df["NEIGHBOURHOOD_158"].isin([area_a, area_b])
        & df["REPORT_DATE"].dt.date.between(
            start_date,
            end_date,
        )
    ].copy()

    if selected_categories:
        comparison_data = comparison_data[
            comparison_data["OFFENCE"].isin(selected_categories)
        ]

    area_a_data = comparison_data[
        comparison_data["NEIGHBOURHOOD_158"] == area_a
    ]

    area_b_data = comparison_data[
        comparison_data["NEIGHBOURHOOD_158"] == area_b
    ]

    metric_a, metric_b = st.columns(2)

    metric_a.metric(
        area_a,
        f"{len(area_a_data):,} records",
    )

    metric_b.metric(
        area_b,
        f"{len(area_b_data):,} records",
    )

    if comparison_data.empty:
        st.info("No records found for these selections.")
    else:
        offence_comparison = (
            comparison_data.groupby(
                ["OFFENCE", "NEIGHBOURHOOD_158"]
            )
            .size()
            .reset_index(name="Records")
        )

        top_offences = (
            comparison_data["OFFENCE"]
            .value_counts()
            .head(8)
            .index
        )

        offence_comparison = offence_comparison[
            offence_comparison["OFFENCE"].isin(top_offences)
        ]

        comparison_chart = px.bar(
            offence_comparison,
            x="OFFENCE",
            y="Records",
            color="NEIGHBOURHOOD_158",
            barmode="group",
            title="Reported Offences by Neighbourhood",
            labels={
                "OFFENCE": "Offence",
                "NEIGHBOURHOOD_158": "Neighbourhood",
            },
        )

        st.plotly_chart(
            comparison_chart,
            use_container_width=True,
        )

st.caption(
    "Comparisons reflect reported records in the selected "
    "dataset, not the overall safety of a neighbourhood. "
    "Differences in population, activity, reporting, and "
    "data coverage can affect these counts."
)

# Toronto Crime Map


st.divider()

st.header("Toronto Crime Map")

st.caption(
    "Select a marker to inspect its reported offence details. "
    "Locations are approximate and may be offset for privacy."
)

map_data = filtered.copy()

map_data["LAT_WGS84"] = pd.to_numeric(
    map_data["LAT_WGS84"],
    errors="coerce",
)

map_data["LONG_WGS84"] = pd.to_numeric(
    map_data["LONG_WGS84"],
    errors="coerce",
)

map_data = map_data.dropna(
    subset=["LAT_WGS84", "LONG_WGS84"]
)

map_data = map_data[
    map_data["LAT_WGS84"].between(43.5, 43.9)
    & map_data["LONG_WGS84"].between(-79.7, -79.1)
].copy()

if map_data.empty:
    st.info(
        "No mapped records are available for the "
        "selected filters."
    )
else:
    map_data["Report Date"] = pd.to_datetime(
        map_data["REPORT_DATE"],
        utc=True,
    ).dt.strftime("%B %d, %Y")

    map_data["Neighbourhood"] = (
        map_data["NEIGHBOURHOOD_158"]
        .fillna("Unknown")
    )

    map_data["Offence"] = (
        map_data["OFFENCE"]
        .fillna("Unknown")
    )

    map_data["Division"] = (
        map_data["DIVISION"]
        .fillna("Unknown")
        .astype(str)
    )

    map_data = map_data.reset_index(drop=True)

    fig = px.scatter_map(
        map_data,
        lat="LAT_WGS84",
        lon="LONG_WGS84",
        hover_name="Offence",
        hover_data={
            "Neighbourhood": True,
            "Report Date": True,
            "LAT_WGS84": False,
            "LONG_WGS84": False,
        },
        custom_data=[
            "Offence",
            "Neighbourhood",
            "Report Date",
            "Division",
        ],
        zoom=10,
        center={
            "lat": 43.72,
            "lon": -79.38,
        },
        map_style="open-street-map",
        height=550,
    )

    fig.update_traces(
        marker={
            "size": 9,
            "color": "#ef4444",
            "opacity": 0.75,
        }
    )

    fig.update_layout(
        margin={
            "l": 0,
            "r": 0,
            "t": 0,
            "b": 0,
        }
    )

    selection = st.plotly_chart(
        fig,
        use_container_width=True,
        key="crime_map",
        on_select="rerun",
        selection_mode="points",
    )

    st.caption(
        f"Displaying {len(map_data):,} records "
        "with valid published coordinates."
    )

    selected_points = selection.selection.points

    if selected_points:
        point = selected_points[0]
        details = point.get("customdata", [])

        if len(details) >= 4:
            st.subheader("Selected Incident")

            col1, col2 = st.columns(2)

            col1.write(
                f"**Offence:** {details[0]}"
            )

            col1.write(
                f"**Neighbourhood:** {details[1]}"
            )

            col2.write(
                f"**Report Date:** {details[2]}"
            )

            col2.write(
                f"**Police Division:** {details[3]}"
            )
    else:
        st.info(
            "Click a red marker to view its "
            "reported incident details."
        )

st.warning(
    "Incident coordinates are approximate published "
    "locations and may be geographically offset. "
    "Markers do not represent exact addresses, "
    "ongoing emergencies, or neighbourhood safety ratings."
)
