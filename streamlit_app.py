import streamlit as st
import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_PATH = ROOT_DIR / "outputs" / "cleaned_debt_dataset.csv"

st.set_page_config(page_title="International Debt Dashboard", layout="wide")


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Country_Name"] = df["Country_Name"].astype(str).str.strip()
    df["Country_Code"] = df["Country_Code"].astype(str).str.strip()
    df["Series_Name"] = df["Series_Name"].astype(str).str.strip()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Debt_Value"] = pd.to_numeric(df["Debt_Value"], errors="coerce")
    return df.dropna(subset=["Year", "Debt_Value"]).reset_index(drop=True)


def filter_data(df: pd.DataFrame) -> pd.DataFrame:
    min_year = int(df["Year"].min())
    max_year = int(df["Year"].max())

    year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))
    all_countries = sorted(df["Country_Name"].dropna().unique())
    default_countries = all_countries[:10]
    selected_countries = st.sidebar.multiselect("Countries", all_countries, default=default_countries)

    all_indicators = sorted(df["Series_Name"].dropna().unique())
    selected_indicators = st.sidebar.multiselect("Indicators", all_indicators, default=all_indicators[:10])

    filtered = df[(df["Year"] >= year_range[0]) & (df["Year"] <= year_range[1])].copy()

    if selected_countries:
        filtered = filtered[filtered["Country_Name"].isin(selected_countries)]
    if selected_indicators:
        filtered = filtered[filtered["Series_Name"].isin(selected_indicators)]

    return filtered


def main() -> None:
    df = load_data(DATA_PATH)
    filtered = filter_data(df)

    st.title("International Debt Analysis Dashboard")
    st.caption("Simple interactive dashboard built from the cleaned debt dataset")

    if filtered.empty:
        st.warning("No data matches the selected filters.")
        return

    country_summary = (
        filtered.groupby("Country_Name", as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Total_Debt", ascending=False)
    )
    indicator_summary = (
        filtered.groupby("Series_Name", as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Total_Debt", ascending=False)
    )
    yearly_summary = (
        filtered.groupby("Year", as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Year")
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Debt", f"${filtered['Debt_Value'].sum():,.2f}")
    col2.metric("Average Debt", f"${filtered['Debt_Value'].mean():,.2f}")
    col3.metric("Countries", f"{filtered['Country_Name'].nunique()}")
    col4.metric("Indicators", f"{filtered['Series_Name'].nunique()}")

    st.subheader("Top Countries by Total Debt")
    top_countries = country_summary.head(10)
    st.bar_chart(top_countries.set_index("Country_Name")["Total_Debt"]) 

    st.subheader("Top Indicators by Total Debt")
    top_indicators = indicator_summary.head(10)
    st.bar_chart(top_indicators.set_index("Series_Name")["Total_Debt"]) 

    st.subheader("Yearly Debt Trend")
    st.line_chart(yearly_summary.set_index("Year")["Total_Debt"]) 

    st.subheader("Dataset Preview")
    st.dataframe(filtered.head(200), use_container_width=True)


if __name__ == "__main__":
    main()
