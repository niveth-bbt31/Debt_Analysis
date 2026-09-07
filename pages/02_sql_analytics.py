from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parents[1] / "outputs" / "cleaned_debt_dataset.csv"


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Debt_Value"] = pd.to_numeric(df["Debt_Value"], errors="coerce")
    return df.dropna(subset=["Year", "Debt_Value"]).reset_index(drop=True)


def basic_queries(df: pd.DataFrame):
    country_names = (
        df["Country_Name"].dropna().drop_duplicates().sort_values().to_frame(name="Country_Name")
    )
    country_count = df["Country_Name"].nunique()
    indicator_count = df["Series_Name"].nunique()
    first_10 = df.head(10)
    total_global_debt = df["Debt_Value"].sum()
    unique_indicators = df["Series_Name"].dropna().drop_duplicates().sort_values().to_frame(name="Series_Name")
    records_by_country = (
        df.groupby("Country_Name", as_index=False).size().rename(columns={"size": "Record_Count"})
    )
    debt_gt_1b = df[df["Debt_Value"] > 1_000_000_000].sort_values("Debt_Value", ascending=False)
    debt_stats = df["Debt_Value"].agg(["min", "max", "mean"]).rename({"min": "Min_Debt", "max": "Max_Debt", "mean": "Average_Debt"})
    total_records = len(df)

    return {
        "1. Retrieve all distinct country names from the dataset.": country_names,
        "2. Count the total number of countries available.": pd.DataFrame({"Total_Countries": [country_count]}),
        "3. Find the total number of indicators present.": pd.DataFrame({"Total_Indicators": [indicator_count]}),
        "4. Display the first 10 records of the dataset.": first_10,
        "5. Calculate the total global debt.": pd.DataFrame({"Total_Global_Debt": [total_global_debt]}),
        "6. List all unique indicator names.": unique_indicators,
        "7. Find the number of records for each country.": records_by_country,
        "8. Display all records where debt is greater than 1 billion USD.": debt_gt_1b,
        "9. Find the minimum, maximum, and average debt values.": debt_stats.to_frame(name="Value").reset_index().rename(columns={"index": "Metric"}),
        "10. Count total number of records in the dataset.": pd.DataFrame({"Total_Records": [total_records]}),
    }


def intermediate_queries(df: pd.DataFrame):
    country_totals = (
        df.groupby("Country_Name", as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Total_Debt", ascending=False)
    )
    avg_debt_per_country = (
        df.groupby("Country_Name", as_index=False)["Debt_Value"]
        .mean()
        .rename(columns={"Debt_Value": "Average_Debt"})
        .sort_values("Average_Debt", ascending=False)
    )
    indicator_totals = (
        df.groupby("Series_Name", as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Total_Debt", ascending=False)
    )
    highest_indicator = indicator_totals.head(1)
    lowest_country = country_totals.sort_values("Total_Debt", ascending=True).head(1)
    country_indicator_totals = (
        df.groupby(["Country_Name", "Series_Name"], as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Total_Debt", ascending=False)
    )
    indicator_count_by_country = (
        df.groupby("Country_Name", as_index=False)["Series_Name"]
        .nunique()
        .rename(columns={"Series_Name": "Indicator_Count"})
        .sort_values("Indicator_Count", ascending=False)
    )
    global_average = country_totals["Total_Debt"].mean()
    countries_above_avg = country_totals[country_totals["Total_Debt"] > global_average].sort_values("Total_Debt", ascending=False)
    ranked_countries = country_totals.assign(Debt_Rank=lambda x: x["Total_Debt"].rank(method="dense", ascending=False).astype(int)).sort_values("Debt_Rank")

    return {
        "1. Find the total debt for each country.": country_totals,
        "2. Display the top 10 countries with the highest total debt.": country_totals.head(10),
        "3. Find the average debt per country.": avg_debt_per_country,
        "4. Calculate total debt for each indicator.": indicator_totals,
        "5. Identify the indicator contributing the highest total debt.": highest_indicator,
        "6. Find the country with the lowest total debt.": lowest_country,
        "7. Calculate total debt for each country and indicator combination.": country_indicator_totals,
        "8. Count how many indicators each country has.": indicator_count_by_country,
        "9. Display countries whose total debt is above the global average.": countries_above_avg,
        "10. Rank countries based on total debt (highest to lowest).": ranked_countries,
    }


def advanced_queries(df: pd.DataFrame):
    indicator_totals = (
        df.groupby("Series_Name", as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Total_Debt", ascending=False)
    )
    top_5_indicators = indicator_totals.head(5)
    country_totals = (
        df.groupby("Country_Name", as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Total_Debt", ascending=False)
    )
    country_contribution = country_totals.assign(
        Percentage_of_Global_Debt=lambda x: x["Total_Debt"] / x["Total_Debt"].sum() * 100
    ).sort_values("Percentage_of_Global_Debt", ascending=False)
    top_3_by_indicator = (
        df.groupby(["Series_Name", "Country_Name"], as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values(["Series_Name", "Total_Debt"], ascending=[True, False])
        .groupby("Series_Name")
        .head(3)
    )
    country_debt_range = (
        df.groupby("Country_Name", as_index=False)["Debt_Value"]
        .agg(["max", "min"])
        .reset_index()
        .rename(columns={"max": "Max_Debt", "min": "Min_Debt"})
    )
    country_debt_range["Debt_Difference"] = country_debt_range["Max_Debt"] - country_debt_range["Min_Debt"]
    top_10_view = country_totals.head(10).copy()
    top_10_view["View_Name"] = "top_10_debt_countries"
    threshold = country_totals["Total_Debt"].mean()
    debt_categories = country_totals.assign(
        Debt_Category=lambda x: x["Total_Debt"].apply(
            lambda y: "High Debt" if y > threshold * 1.5 else "Medium Debt" if y > threshold * 0.75 else "Low Debt"
        )
    )
    countries_by_year = df.sort_values(["Country_Name", "Year"]).copy()
    countries_by_year["Cumulative_Debt"] = countries_by_year.groupby("Country_Name")["Debt_Value"].cumsum()
    indicator_avg_debt = (
        df.groupby("Series_Name", as_index=False)["Debt_Value"]
        .mean()
        .rename(columns={"Debt_Value": "Average_Debt"})
    )
    overall_avg = df["Debt_Value"].mean()
    indicators_above_avg = indicator_avg_debt[indicator_avg_debt["Average_Debt"] > overall_avg].sort_values("Average_Debt", ascending=False)
    global_debt_total = df["Debt_Value"].sum()
    countries_above_5pct = country_contribution[country_contribution["Percentage_of_Global_Debt"] > 5].copy()
    dominant_indicator_per_country = (
        df.groupby(["Country_Name", "Series_Name"], as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values(["Country_Name", "Total_Debt"], ascending=[True, False])
        .groupby("Country_Name")
        .head(1)
        .rename(columns={"Series_Name": "Dominant_Indicator"})
    )

    return {
        "1. Find the top 5 indicators contributing most to global debt.": top_5_indicators,
        "2. Calculate percentage contribution of each country to total global debt.": country_contribution,
        "3. Identify the top 3 countries for each indicator based on debt.": top_3_by_indicator,
        "4. Find the difference between maximum and minimum debt for each country.": country_debt_range[["Country_Name", "Debt_Difference"]].sort_values("Debt_Difference", ascending=False),
        "5. Create a view for the top 10 countries with highest debt.": top_10_view[["Country_Name", "Total_Debt", "View_Name"]],
        "6. Categorize countries into High Debt, Medium Debt, and Low Debt (based on thresholds).": debt_categories[["Country_Name", "Total_Debt", "Debt_Category"]],
        "7. Use window functions to calculate cumulative debt per country.": countries_by_year[["Country_Name", "Year", "Debt_Value", "Cumulative_Debt"]],
        "8. Find indicators where average debt is higher than overall average debt.": indicators_above_avg,
        "9. Identify countries contributing more than 5% of global debt.": countries_above_5pct,
        "10. Find the most dominant indicator (highest contribution) for each country.": dominant_indicator_per_country,
    }


def render_answer(question_key: str, answer_df: pd.DataFrame) -> None:
    st.subheader(question_key)

    if isinstance(answer_df, pd.Series):
        answer_df = answer_df.to_frame(name="Value").reset_index().rename(columns={"index": "Metric"})

    if answer_df.empty:
        st.info("No data available for this query.")
        return

    st.dataframe(answer_df, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Debt SQL Questions", layout="wide")
    df = load_data()

    all_questions = {}
    all_questions.update(basic_queries(df))
    all_questions.update(intermediate_queries(df))
    all_questions.update(advanced_queries(df))

    st.title("International Debt Analysis - SQL Questions")
    st.caption("Choose any question from the dropdown to see the corresponding answer from the cleaned debt dataset.")

    selected_question = st.selectbox("Select a question", list(all_questions.keys()))

    st.markdown("---")
    render_answer(selected_question, all_questions[selected_question])


if __name__ == "__main__":
    main()
