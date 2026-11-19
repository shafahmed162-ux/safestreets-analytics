
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from src.download_crime_data import download_crime_data


DATA_FILE = Path("data/raw/toronto_crime_recent.csv")

st.set_page_config(
    page_title="SafeStreets | Toronto Crime Analytics",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ SafeStreets")
st.subheader("Toronto Crime Analytics & Public Safety Intelligence")

st.caption(
    "Explore reported crime data from Toronto Police Service. "
    "Data is updated when new records are published by the source."
)


@st.cache_data
def load_data():
    if not DATA_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(DATA_FILE)

    df["REPORT_DATE"] = pd.to_datetime(
        df["REPORT_DATE"],
        utc=True,
        errors="coerce",
    )

    return df


df = load_data()


REFRESH_FILE = Path("data/processed/last_refresh.txt")

if REFRESH_FILE.exists():
    last_refresh = pd.to_datetime(
        REFRESH_FILE.read_text().strip(),
        utc=True,
        errors="coerce",
    )

    if pd.notna(last_refresh):
        st.caption(
            "Last successful data refresh: "
            f"{last_refresh:%B %d, %Y at %H:%M UTC}"
        )
    else:
        st.caption("Last successful refresh: Unknown")
else:
    st.caption("Last successful refresh: Not recorded yet")


if df.empty:
    st.error("No crime data found. Run the data downloader first.")
    st.stop()

latest_date = df["REPORT_DATE"].max()
earliest_date = df["REPORT_DATE"].min()

st.info(
    f"Available sample reporting period: "
    f"{earliest_date:%B %d, %Y} – "
    f"{latest_date:%B %d, %Y}. "
    "This dashboard currently uses a 5,000-record development sample."
)

neighbourhoods = sorted(
    df["NEIGHBOURHOOD_158"]
    .dropna()
    .loc[lambda x: x != "NSA"]
    .unique()
    .tolist()
)

with st.sidebar:
    st.header("Explore Crime Data")

    selected_area = st.selectbox(
        "Neighbourhood",
        ["All neighbourhoods"] + neighbourhoods,
    )

    categories = sorted(
        df["OFFENCE"].dropna().unique().tolist()
    )

    selected_categories = st.multiselect(
        "Offence categories",
        categories,
        default=[],
        placeholder="All offence categories",
    )

    start_date, end_date = st.date_input(
        "Report date range",
        value=(
            earliest_date.date(),
            latest_date.date(),
        ),
        min_value=earliest_date.date(),
        max_value=latest_date.date(),
    )

filtered = df.copy()

if selected_area != "All neighbourhoods":
    filtered = filtered[
        filtered["NEIGHBOURHOOD_158"] == selected_area
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
    filtered["NEIGHBOURHOOD_158"].nunique(),
)

col3.metric(
    "Offence categories",
    filtered["OFFENCE"].nunique(),
)

st.divider()

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

left, right = st.columns(2)

with left:
    st.subheader("Most Common Reported Offences")

    offence_counts = (
        filtered["OFFENCE"]
        .value_counts()
        .head(10)
        .reset_index()
    )

    offence_counts.columns = ["Offence", "Records"]

    offence_chart = px.bar(
        offence_counts,
        x="Records",
        y="Offence",
        orientation="h",
        title="Top 10 Offences",
    )

    offence_chart.update_layout(
        yaxis={"categoryorder": "total ascending"}
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
        .reset_index(name="Records")
    )

    daily_counts.columns = ["Date", "Records"]

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
    "Records may be preliminary and incident locations may be "
    "geographically offset for privacy. "
    "Counts are not population-adjusted crime rates."
)


st.divider()

refresh_col, status_col = st.columns([1, 3])

with refresh_col:
    refresh_clicked = st.button(
        "🔄 Refresh Crime Data",
        use_container_width=True,
    )

if refresh_clicked:
    try:
        with st.spinner(
            "Checking Toronto Police for updated crime records..."
        ):
            download_crime_data()
            load_data.clear()

        st.success("Crime data refreshed successfully!")
        st.rerun()

    except Exception as error:
        st.error(f"Data refresh failed: {error}")

with status_col:
    st.caption(
        "Refresh retrieves the latest 5,000 records available "
        "from the Toronto Police public dataset."
    )

