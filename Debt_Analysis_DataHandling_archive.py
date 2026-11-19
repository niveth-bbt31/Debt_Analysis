from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT_DIR = Path(__file__).resolve().parent
DATASET_PATH = ROOT_DIR / "resources" / "Datasets_CSV" / "IDS_ALLCountries_Data.csv"
OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def clean_debt_data(file_path: Path) -> pd.DataFrame:
    """Load the debt CSV, clean column names, handle missing values, and reshape to long format."""
    raw_df = pd.read_csv(file_path, encoding="cp1252")
    raw_df = raw_df.dropna(how="all").copy()

    raw_df.columns = (
        raw_df.columns.astype(str)
        .str.replace(r"[\(\)]", "", regex=True)
        .str.replace(r"[$/\-%]", "", regex=True)
        .str.replace(r"\s+", "_", regex=True)
        .str.strip()
    )

    text_columns = [
        "Country_Name",
        "Country_Code",
        "CounterpartArea_Name",
        "CounterpartArea_Code",
        "Series_Name",
        "Series_Code",
    ]
    for column in text_columns:
        raw_df[column] = raw_df[column].fillna("Unknown")

    year_columns = [str(year) for year in range(2000, 2033)]
    for col in year_columns:
        raw_df[col] = pd.to_numeric(raw_df[col], errors="coerce")
    raw_df[year_columns] = raw_df[year_columns].fillna(0)

    raw_df = raw_df.drop_duplicates(subset=["Country_Code", "CounterpartArea_Code", "Series_Code"]).copy()

    id_columns = [
        "Country_Name",
        "Country_Code",
        "CounterpartArea_Name",
        "CounterpartArea_Code",
        "Series_Name",
        "Series_Code",
    ]
    long_df = raw_df.melt(
        id_vars=id_columns,
        value_vars=year_columns,
        var_name="Year",
        value_name="Debt_Value",
    )

    long_df["Year"] = pd.to_numeric(long_df["Year"], errors="coerce")
    long_df["Debt_Value"] = pd.to_numeric(long_df["Debt_Value"], errors="coerce")
    long_df = long_df.dropna(subset=["Year", "Debt_Value"]).reset_index(drop=True)

    return long_df


def summarize_debt(df: pd.DataFrame) -> dict:
    country_summary = (
        df.groupby("Country_Name", as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Total_Debt", ascending=False)
    )
    indicator_summary = (
        df.groupby("Series_Name", as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Total_Debt", ascending=False)
    )
    yearly_summary = (
        df.groupby("Year", as_index=False)["Debt_Value"]
        .sum()
        .rename(columns={"Debt_Value": "Total_Debt"})
        .sort_values("Year")
    )

    summary = {
        "total_countries": df["Country_Code"].nunique(),
        "total_indicators": df["Series_Code"].nunique(),
        "total_global_debt": df["Debt_Value"].sum(),
        "average_debt": df["Debt_Value"].mean(),
        "median_debt": df["Debt_Value"].median(),
        "min_debt": df["Debt_Value"].min(),
        "max_debt": df["Debt_Value"].max(),
        "country_summary": country_summary,
        "indicator_summary": indicator_summary,
        "yearly_summary": yearly_summary,
    }
    return summary


def save_visualizations(summary: dict) -> None:
    top_countries = summary["country_summary"].head(10)
    top_indicators = summary["indicator_summary"].head(10)
    yearly_trend = summary["yearly_summary"]

    plt.figure(figsize=(12, 7))
    sns.barplot(data=top_countries, x="Total_Debt", y="Country_Name", hue="Country_Name", dodge=False, legend=False, palette="viridis")
    plt.title("Top 10 Countries by Total Debt")
    plt.xlabel("Total Debt")
    plt.ylabel("Country")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "top_countries_debt.png", dpi=200)
    plt.close()

    plt.figure(figsize=(12, 7))
    sns.barplot(data=top_indicators, x="Total_Debt", y="Series_Name", hue="Series_Name", dodge=False, legend=False, palette="magma")
    plt.title("Top 10 Debt Indicators by Total Debt")
    plt.xlabel("Total Debt")
    plt.ylabel("Indicator")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "top_indicators_debt.png", dpi=200)
    plt.close()

    plt.figure(figsize=(12, 6))
    sns.lineplot(data=yearly_trend, x="Year", y="Total_Debt", marker="o")
    plt.title("Yearly Global Debt Trend")
    plt.xlabel("Year")
    plt.ylabel("Total Debt")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "yearly_debt_trend.png", dpi=200)
    plt.close()


def print_summary(summary: dict) -> None:
    print("\n=== International Debt Analysis Summary ===")
    print(f"Total countries: {summary['total_countries']}")
    print(f"Total indicators: {summary['total_indicators']}")
    print(f"Total global debt: ${summary['total_global_debt']:,.2f}")
    print(f"Average debt: ${summary['average_debt']:,.2f}")
    print(f"Median debt: ${summary['median_debt']:,.2f}")
    print(f"Minimum debt: ${summary['min_debt']:,.2f}")
    print(f"Maximum debt: ${summary['max_debt']:,.2f}")
    print("\nTop 10 countries by total debt:")
    print(summary["country_summary"].head(10).to_string(index=False))
    print("\nTop 10 indicators by total debt:")
    print(summary["indicator_summary"].head(10).to_string(index=False))


def main() -> None:
    cleaned_df = clean_debt_data(DATASET_PATH)
    cleaned_df.to_csv(OUTPUT_DIR / "cleaned_debt_dataset.csv", index=False)

    summary = summarize_debt(cleaned_df)
    summary["country_summary"].to_csv(OUTPUT_DIR / "country_debt_summary.csv", index=False)
    summary["indicator_summary"].to_csv(OUTPUT_DIR / "indicator_debt_summary.csv", index=False)
    summary["yearly_summary"].to_csv(OUTPUT_DIR / "yearly_debt_summary.csv", index=False)

    print_summary(summary)
    save_visualizations(summary)

    print(f"\nCleaned dataset saved to: {OUTPUT_DIR / 'cleaned_debt_dataset.csv'}")
    print(f"Visual outputs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()