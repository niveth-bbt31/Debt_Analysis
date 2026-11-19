import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT_DIR = Path(__file__).resolve().parent
DATASET_PATH = ROOT_DIR / "resources" / "Datasets_CSV" / "IDS_ALLCountries_Data.csv"
OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
DB_PATH = OUTPUT_DIR / "international_debt_analysis.db"

#=====================Read CSv file to DataFrame and clean the data=========================
raw_df = pd.read_csv(DATASET_PATH, encoding="cp1252")
raw_df = raw_df.dropna(how="all").copy()  #duplicates removed
raw_df[["Country Name", "Country Code", "Counterpart-Area Name", "Counterpart-Area Code", "Series Name", "Series Code"]] = raw_df[["Country Name", "Country Code", "Counterpart-Area Name", "Counterpart-Area Code", "Series Name", "Series Code"]].fillna("Unknown")
raw_df.columns = (
    raw_df.columns.astype(str)
    .str.replace(r"[()\[\]]", "", regex=True)
    .str.replace(r"[$/%-]", "", regex=True)
    .str.replace(r"\s+", "_", regex=True)
    .str.strip()
)
#------------the year column into clean long-format dataset for analysis and visualization------------------
year_columns = [str(year) for year in range(2000, 2033)]
available_years = [col for col in year_columns if col in raw_df.columns]
for col in available_years:
    raw_df[col] = pd.to_numeric(raw_df[col], errors="coerce")
raw_df[available_years] = raw_df[available_years].fillna(0)

melted_df = raw_df.melt(
    id_vars=["Country_Name", "Country_Code", "CounterpartArea_Name", "CounterpartArea_Code", "Series_Name", "Series_Code"],
    value_vars=available_years,
    var_name="Year",
    value_name="Debt_Value",
)

melted_df["Year"] = pd.to_numeric(melted_df["Year"], errors="coerce")
melted_df["Debt_Value"] = pd.to_numeric(melted_df["Debt_Value"], errors="coerce")
melted_df = melted_df.dropna(subset=["Year", "Debt_Value"]).reset_index(drop=True)

###############DB Connection and Table Creation#####################

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")    # enforce foreign key relationships so child records cannot point to non-existent parent IDs
#Drop the table already exists to avoid duplicate table creation errors when running the script multiple times
conn.execute("DROP TABLE IF EXISTS debt_data")
conn.execute("DROP TABLE IF EXISTS indicators")
conn.execute("DROP TABLE IF EXISTS countries")

#Create new tables for countries, indicators, and debt_data with appropriate columns and foreign key relationships
conn.execute(
    """
    CREATE TABLE countries (
        country_id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_name TEXT NOT NULL,
        country_code TEXT NOT NULL
    )
    """
)

conn.execute(
    """
    CREATE TABLE indicators (
        indicator_id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_name TEXT NOT NULL,
        series_code TEXT NOT NULL
    )
    """
)

conn.execute(
    """
    CREATE TABLE debt_data (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        indicator_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        debt_value REAL NOT NULL,
        FOREIGN KEY (country_id) REFERENCES countries(country_id),
        FOREIGN KEY (indicator_id) REFERENCES indicators(indicator_id)
    )
    """
)

#-------------------Drop duplicates and rename the columns for database insertion----------------------------
country_rows = (
    melted_df[["Country_Name", "Country_Code"]]
    .drop_duplicates()
    .rename(columns={"Country_Name": "country_name", "Country_Code": "country_code"})
    .itertuples(index=False, name=None)
)

indicator_rows = (
    melted_df[["Series_Name", "Series_Code"]]
    .drop_duplicates()
    .rename(columns={"Series_Name": "series_name", "Series_Code": "series_code"})
    .itertuples(index=False, name=None)
)
#-------------------Insert data into the database tables----------------------------
country_inserts = [(country_name, country_code) for country_name, country_code in country_rows]
indicator_inserts = [(series_name, series_code) for series_name, series_code in indicator_rows]

conn.executemany("INSERT INTO countries (country_name, country_code) VALUES (?, ?)", country_inserts)
conn.executemany("INSERT INTO indicators (series_name, series_code) VALUES (?, ?)", indicator_inserts)

country_map = dict(
    conn.execute("SELECT country_name, country_id FROM countries").fetchall()
)
indicator_map = dict(
    conn.execute("SELECT series_name, indicator_id FROM indicators").fetchall()
)

records = []
for row in melted_df[["Country_Name", "Series_Name", "Year", "Debt_Value"]].itertuples(index=False, name=None):
    country_name, series_name, year, debt_value = row
    country_id = country_map.get(country_name)
    indicator_id = indicator_map.get(series_name)
    if country_id is not None and indicator_id is not None:
        records.append((country_id, indicator_id, int(year), float(debt_value)))

conn.executemany(
    "INSERT INTO debt_data (country_id, indicator_id, year, debt_value) VALUES (?, ?, ?, ?)",
    records,
)
conn.commit()

def read_sql_query(sql_query: str, db_path: str) -> pd.DataFrame:
    """
    Execute a SQL query and return the result as a pandas DataFrame.
    """
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(sql_query, conn)

#========================================================================================
# Function to generate Plotly chart based on the question and DataFrame
#=======================================================================================
def generate_plotly_chart(q_name: str, df: pd.DataFrame):
    """Returns a Plotly figure for queries where visualization is meaningful, else None."""
    if df.empty:
        return None

    # 1. Skip single-cell counts/totals & single-column text lists
    if df.shape == (1, 1) or df.shape[1] == 1:
        return None

    # 2. Basic 9: Min, Max, and Average Debt -> Comparison Bar Chart
    if q_name.startswith("Q9:"):
        melted = df.melt(var_name="Metric", value_name="Debt_USD")
        fig = px.bar(
            melted,
            x="Metric",
            y="Debt_USD",
            color="Metric",
            title="Global Debt Summary (Min, Max, Average)",
            text_auto=".2s",
        )
        return fig

    # 3. Basic 4 & 8: Record-level outputs -> Horizontal Bar of Top 15 Records
    if q_name.startswith(("Q4:", "Q8:")):
        top_df = ans_dataframe_df.head(15).copy()
        top_df["Country_Year"] = (
            top_df["country_name"] + " (" + top_df["year"].astype(str) + ")"
        )
        fig = px.bar(
            top_df,
            x="debt_value",
            y="Country_Year",
            color="series_name",
            orientation="h",
            title=f"{q_name} (Top 15 Shown)",
            text_auto=".2s",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
        return fig
    #Q20: Rank countries by total debt -> Horizontal Bar of Top 15 Countries
    if q_name.startswith("Q20:"):
        top_df = top_ranked_df = ans_dataframe_df.head(15).copy()
        top_ranked_df["Rank_Label"] = "#" + top_ranked_df["debt_rank"].astype(str) + " " + top_ranked_df["country_name"]
        fig = px.bar(
            top_ranked_df,
            x="total_debt",
            y="Rank_Label",
            orientation="h",
            color="total_debt",
            color_continuous_scale="Blues",
            text_auto=".2s",
            title="Top 15 Countries Ranked by Total Debt",
            labels={"total_debt": "Total Debt (USD)", "Rank_Label": "Rank & Country"}
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
            height=500
        )
        return fig

    #  Q12: Display the top 10 countries with the highest total debt.
    if q_name.startswith("Q12:"):
        top_df = ans_dataframe_df.head(10).copy()
        fig = px.bar(
            top_df,
            x="country_name",
            y="total_debt",
            color="total_debt",
            color_continuous_scale="Reds",
            text_auto=".2s",
            title="Top 10 Countries by Total Debt",
            labels={"country_name": "Country", "total_debt": "Total Debt (USD)"}
        )
        fig.update_layout(
            xaxis_title="Country",
            yaxis_title="Total Debt (USD)",
            coloraxis_showscale=False
        )
        return fig

    # Q13: the average debt per country.
    if q_name.startswith("Q13:"):
        top_avg_df = ans_dataframe_df.head(15).copy()

        fig = px.bar(
            top_avg_df,
            x="average_debt",
            y="country_name",
            orientation="h",
            color="average_debt",
            color_continuous_scale="Tealgrn",
            text_auto=".2s",
            title="Top 15 Countries by Average Debt",
            labels={"average_debt": "Average Debt (USD)", "country_name": "Country"}
        )

        # Put the highest average debt at the top and hide the color scale legend
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
            height=500
        )
        return fig

    # Q14: Calculate total debt for each indicator.
    if q_name.startswith("Q14:"):
        top_ind_df = ans_dataframe_df.head(15).copy()

        # Shorten long indicator names for the Y-axis while keeping full names for hover tooltips
        top_ind_df["short_name"] = top_ind_df["series_name"].apply(
            lambda x: x[:45] + "..." if len(str(x)) > 45 else str(x)
        )

        fig = px.bar(
            top_ind_df,
            x="total_debt",
            y="short_name",
            orientation="h",
            color="total_debt",
            color_continuous_scale="Purples",
            hover_data={"series_name": True, "short_name": False, "total_debt": ":,.2f"},
            text_auto=".2s",
            title="Top 15 Debt Indicators by Total Debt",
            labels={"total_debt": "Total Debt (USD)", "short_name": "Indicator", "series_name": "Full Indicator Name"}
        )

        # Put the highest total debt indicator at the top and hide the color legend
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
            height=550
        )
        return fig
    # Q17:  total debt for each country and indicator combination.
    top_ind_df = ans_dataframe_df.head(15).copy()

    # Shorten long indicator names for the Y-axis while keeping full names for hover tooltips
    top_ind_df["short_name"] = top_ind_df["series_name"].apply(
        lambda x: x[:45] + "..." if len(str(x)) > 45 else str(x)
    )

    fig = px.bar(
        top_ind_df,
        x="total_debt",
        y="short_name",
        orientation="h",
        color="total_debt",
        color_continuous_scale="Purples",
        hover_data={"series_name": True, "short_name": False, "total_debt": ":,.2f"},
        text_auto=".2s",
        title="Top 15 Debt Indicators by Total Debt",
        labels={"total_debt": "Total Debt (USD)", "short_name": "Indicator", "series_name": "Full Indicator Name"}
    )

    # Put the highest total debt indicator at the top and hide the color legend
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        coloraxis_showscale=False,
        height=550
    )
    return fig

# ======================================================================================================================
# APPLICATION INTERFACE NAVIGATION
# ======================================================================================================================
page = st.sidebar.radio("Navigation Menu",["Dashboard","Q&A Page"])

# ======================================================================================================================
# 1. DASHBOARD PAGE
# ======================================================================================================================

if page == "Dashboard":
    st.title("International Debt Analysis Dashboard")
    st.caption("SQLite-backed dashboard and SQL-driven question answering")
#--------------------------------Sidebar Filters---------------------------------
    with st.sidebar:
        st.header("Controls")
        year_min = int(melted_df["Year"].min())
        year_max = int(melted_df["Year"].max())
        selected_years = st.slider("Filter year range", year_min, year_max, (year_min, year_max))
        country_options = sorted(melted_df["Country_Name"].dropna().unique().tolist())
        selected_countries = st.multiselect("Countries", country_options, default=country_options[:10])
        indicator_options = sorted(melted_df["Series_Name"].dropna().unique().tolist())
        selected_indicators = st.multiselect("Indicators", indicator_options, default=indicator_options[:10])

    filtered_query = """
    SELECT d.country_id, d.indicator_id, d.year, d.debt_value, c.country_name, i.series_name
    FROM debt_data d
    JOIN countries c ON c.country_id = d.country_id
    JOIN indicators i ON i.indicator_id = d.indicator_id
    WHERE d.year BETWEEN ? AND ?
    """

    filtered_params = [selected_years[0], selected_years[1]]
    filtered_df = pd.read_sql_query(filtered_query, conn, params=filtered_params)

    if selected_countries:
        filtered_df = filtered_df[filtered_df["country_name"].isin(selected_countries)]
    if selected_indicators:
        filtered_df = filtered_df[filtered_df["series_name"].isin(selected_indicators)]

    if filtered_df.empty:
        st.warning("No records match the selected filters.")
        st.stop()

    country_summary = (
        filtered_df.groupby("country_name", as_index=False)["debt_value"]
        .sum()
        .rename(columns={"debt_value": "total_debt"})
        .sort_values("total_debt", ascending=False)
    )
    indicator_summary = (
        filtered_df.groupby("series_name", as_index=False)["debt_value"]
        .sum()
        .rename(columns={"debt_value": "total_debt"})
        .sort_values("total_debt", ascending=False)
    )
    yearly_summary = (
        filtered_df.groupby("year", as_index=False)["debt_value"]
        .sum()
        .rename(columns={"debt_value": "total_debt"})
        .sort_values("year")
    )
    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Debt", f"${filtered_df['debt_value'].sum():,.2f}")
    metric_cols[1].metric("Average Debt", f"${filtered_df['debt_value'].mean():,.2f}")
    metric_cols[2].metric("Countries", f"{filtered_df['country_name'].nunique()}")
    metric_cols[3].metric("Indicators", f"{filtered_df['series_name'].nunique()}")

    st.subheader("Top countries by total debt")
    st.bar_chart(country_summary.head(10).set_index("country_name")["total_debt"])

    st.subheader("Top indicators by total debt")
    st.bar_chart(indicator_summary.head(10).set_index("series_name")["total_debt"])

    st.subheader("Yearly debt trend")
    st.line_chart(yearly_summary.set_index("year")["total_debt"])

    st.subheader("Filtered dataset preview")
    st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True, hide_index=True)

# =========================================================================
# PAGE 2: BUSINESS STRATEGY Q&A PORTAL
# =========================================================================
elif page == "Q&A Page":
    st.title("International Debt Analysis Q&A Portal")
    st.caption("Select a question to view the SQL query and its results")
    question_sql = {
    "Q1:Distinct country names": """SELECT DISTINCT country_name FROM countries ORDER BY country_name;""",
    "Q2:Total countries": """SELECT COUNT(*) AS total_countries FROM countries;""",
    "Q3:Total indicators": """SELECT COUNT(*) AS total_indicators FROM indicators;""",
    "Q4:First 10 records": """
        SELECT d.record_id, c.country_name, i.series_name, d.year, d.debt_value
        FROM debt_data d
        JOIN countries c ON d.country_id = c.country_id
        JOIN indicators i ON d.indicator_id = i.indicator_id
        LIMIT 10;
    """,
    "Q5:Total global debt": """SELECT ROUND(SUM(debt_value), 2) AS total_global_debt FROM debt_data;""",
    "Q6:Unique indicator names": """SELECT DISTINCT series_name FROM indicators ORDER BY series_name;""",
    "Q7:Number of records per country": """
        SELECT c.country_name, COUNT(d.record_id) AS record_count
        FROM countries c
        LEFT JOIN debt_data d ON c.country_id = d.country_id
        GROUP BY c.country_id, c.country_name
        ORDER BY record_count DESC;
    """,
    "Q8: Records with debt > 1 Billion USD": """
        SELECT d.record_id, c.country_name, i.series_name, d.year, d.debt_value
        FROM debt_data d
        JOIN countries c ON d.country_id = c.country_id
        JOIN indicators i ON d.indicator_id = i.indicator_id
        WHERE d.debt_value > 1000000000
        ORDER BY d.debt_value DESC;
    """,
    "Q9: Min, Max, and Average debt": """
        SELECT MIN(debt_value) AS min_debt, MAX(debt_value) AS max_debt, ROUND(AVG(debt_value), 2) AS avg_debt
        FROM debt_data;
    """,
    "Q10: Total number of records": "SELECT COUNT(*) AS total_records FROM debt_data;",
    #--- INTERMEDIATE QUERIES ---
    "Q11: Total debt per country": """
        SELECT c.country_name, ROUND(SUM(d.debt_value), 2) AS total_debt
        FROM debt_data d JOIN countries c ON d.country_id = c.country_id
        GROUP BY c.country_id, c.country_name ORDER BY total_debt DESC;
    """,
    "Q12: Top 10 countries by total debt": """
        SELECT c.country_name, ROUND(SUM(d.debt_value), 2) AS total_debt
        FROM debt_data d JOIN countries c ON d.country_id = c.country_id
        GROUP BY c.country_id, c.country_name ORDER BY total_debt DESC LIMIT 10;
    """,
    "Q13: Average debt per country": """
        SELECT c.country_name, ROUND(AVG(d.debt_value), 2) AS average_debt
        FROM debt_data d JOIN countries c ON d.country_id = c.country_id
        GROUP BY c.country_id, c.country_name ORDER BY average_debt DESC;
    """,
    "Q14: Total debt per indicator": """
        SELECT i.series_name, ROUND(SUM(d.debt_value), 2) AS total_debt
        FROM debt_data d JOIN indicators i ON d.indicator_id = i.indicator_id
        GROUP BY i.indicator_id, i.series_name ORDER BY total_debt DESC;
    """,
    "Q15: Highest debt indicator": """
        SELECT i.series_name, ROUND(SUM(d.debt_value), 2) AS total_debt
        FROM debt_data d JOIN indicators i ON d.indicator_id = i.indicator_id
        GROUP BY i.indicator_id, i.series_name ORDER BY total_debt DESC LIMIT 1;
    """,
    "Q16: Country with lowest total debt": """
        SELECT c.country_name, ROUND(SUM(d.debt_value), 2) AS total_debt
        FROM debt_data d JOIN countries c ON d.country_id = c.country_id
        GROUP BY c.country_id, c.country_name ORDER BY total_debt ASC LIMIT 1;
    """,
    "Q17: Total debt per country & indicator": """
        SELECT c.country_name, i.series_name, ROUND(SUM(d.debt_value), 2) AS total_debt
        FROM debt_data d
        JOIN countries c ON d.country_id = c.country_id
        JOIN indicators i ON d.indicator_id = i.indicator_id
        GROUP BY c.country_id, c.country_name, i.indicator_id, i.series_name
        ORDER BY c.country_name, total_debt DESC;
    """,
    "Q18: Indicator count per country": """
        SELECT c.country_name, COUNT(DISTINCT d.indicator_id) AS indicator_count
        FROM countries c LEFT JOIN debt_data d ON c.country_id = d.country_id
        GROUP BY c.country_id, c.country_name ORDER BY indicator_count DESC;
    """,
    "Q19: Countries above global average debt": """
        WITH country_totals AS (
            SELECT c.country_name, SUM(d.debt_value) AS total_debt
            FROM debt_data d JOIN countries c ON d.country_id = c.country_id
            GROUP BY c.country_id, c.country_name
        )
        SELECT country_name, ROUND(total_debt, 2) AS total_debt
        FROM country_totals
        WHERE total_debt > (SELECT AVG(total_debt) FROM country_totals)
        ORDER BY total_debt DESC;
    """,
    "Q20: Rank countries by total debt": """
        SELECT RANK() OVER (ORDER BY SUM(d.debt_value) DESC) AS debt_rank,
               c.country_name, ROUND(SUM(d.debt_value), 2) AS total_debt
        FROM debt_data d JOIN countries c ON d.country_id = c.country_id
        GROUP BY c.country_id, c.country_name;
    """,
# --- ADVANCED QUERIES ---
    "Q21: Top 5 indicators contributing to global debt": """
        SELECT i.series_name, ROUND(SUM(d.debt_value), 2) AS total_debt
        FROM debt_data d JOIN indicators i ON d.indicator_id = i.indicator_id
        GROUP BY i.indicator_id, i.series_name ORDER BY total_debt DESC LIMIT 5;
    """,
    "Q22: Percentage contribution per country": """
        SELECT c.country_name, ROUND(SUM(d.debt_value), 2) AS country_debt,
               ROUND((SUM(d.debt_value) * 100.0) / (SELECT SUM(debt_value) FROM debt_data), 2) AS pct_contribution
        FROM debt_data d JOIN countries c ON d.country_id = c.country_id
        GROUP BY c.country_id, c.country_name ORDER BY pct_contribution DESC;
    """,
    "Q23: Top 3 countries per indicator": """
        WITH ranked_countries AS (
            SELECT i.series_name, c.country_name, SUM(d.debt_value) AS total_debt,
                   DENSE_RANK() OVER (PARTITION BY i.indicator_id ORDER BY SUM(d.debt_value) DESC) AS rnk
            FROM debt_data d
            JOIN countries c ON d.country_id = c.country_id
            JOIN indicators i ON d.indicator_id = i.indicator_id
            GROUP BY i.indicator_id, i.series_name, c.country_id, c.country_name
        )
        SELECT series_name, rnk, country_name, ROUND(total_debt, 2) AS total_debt
        FROM ranked_countries WHERE rnk <= 3 ORDER BY series_name, rnk;
    """,
    "Q24: Max vs Min debt difference per country": """
        SELECT c.country_name, ROUND(MAX(d.debt_value), 2) AS max_debt,
               ROUND(MIN(d.debt_value), 2) AS min_debt,
               ROUND(MAX(d.debt_value) - MIN(d.debt_value), 2) AS debt_range
        FROM debt_data d JOIN countries c ON d.country_id = c.country_id
        GROUP BY c.country_id, c.country_name ORDER BY debt_range DESC;
    """,
    "Q25: Query Top 10 Debt View": "SELECT * FROM top_10_debt_countries;",
    "Q26: Categorize countries by debt tier": """
        SELECT c.country_name, ROUND(SUM(d.debt_value), 2) AS total_debt,
               CASE
                   WHEN SUM(d.debt_value) >= 100000000000 THEN 'High Debt'
                   WHEN SUM(d.debt_value) >= 10000000000 THEN 'Medium Debt'
                   ELSE 'Low Debt'
               END AS debt_category
        FROM debt_data d JOIN countries c ON d.country_id = c.country_id
        GROUP BY c.country_id, c.country_name ORDER BY total_debt DESC;
    """,
    "Q27: Cumulative debt per country over time": """
        WITH yearly_country_debt AS (
            SELECT c.country_name, d.year, SUM(d.debt_value) AS yearly_debt
            FROM debt_data d JOIN countries c ON d.country_id = c.country_id
            GROUP BY c.country_id, c.country_name, d.year
        )
        SELECT country_name, year, ROUND(yearly_debt, 2) AS yearly_debt,
               ROUND(SUM(yearly_debt) OVER (PARTITION BY country_name ORDER BY year), 2) AS cumulative_debt
        FROM yearly_country_debt ORDER BY country_name, year;
    """,
    "Q28: Indicators above overall average debt": """
        SELECT i.series_name, ROUND(AVG(d.debt_value), 2) AS indicator_avg_debt
        FROM debt_data d JOIN indicators i ON d.indicator_id = i.indicator_id
        GROUP BY i.indicator_id, i.series_name
        HAVING AVG(d.debt_value) > (SELECT AVG(debt_value) FROM debt_data)
        ORDER BY indicator_avg_debt DESC;
    """,
    "Q29: Countries contributing > 5% of global debt": """
        SELECT c.country_name, ROUND(SUM(d.debt_value), 2) AS country_debt,
               ROUND((SUM(d.debt_value) * 100.0) / (SELECT SUM(debt_value) FROM debt_data), 2) AS pct_contribution
        FROM debt_data d JOIN countries c ON d.country_id = c.country_id
        GROUP BY c.country_id, c.country_name
        HAVING (SUM(d.debt_value) * 100.0) / (SELECT SUM(debt_value) FROM debt_data) > 5.0
        ORDER BY pct_contribution DESC;
    """,
    "Q30: Most dominant indicator per country": """
        WITH country_indicator_totals AS (
            SELECT c.country_name, i.series_name, SUM(d.debt_value) AS total_debt,
                   ROW_NUMBER() OVER (PARTITION BY c.country_id ORDER BY SUM(d.debt_value) DESC) AS rn
            FROM debt_data d
            JOIN countries c ON d.country_id = c.country_id
            JOIN indicators i ON d.indicator_id = i.indicator_id
            GROUP BY c.country_id, c.country_name, i.indicator_id, i.series_name
        )
        SELECT country_name, series_name AS dominant_indicator, ROUND(total_debt, 2) AS total_debt
        FROM country_indicator_totals WHERE rn = 1 ORDER BY total_debt DESC;
    """
    }

    selected_question = st.selectbox("Choose a question",list(question_sql.keys()) )
    target_sql_statement = question_sql[selected_question]
    with st.expander("Inspect Underlying Precompiled SQL Engine Logic", expanded=False):
        st.code(target_sql_statement, language='sql')

    st.write("### Tabular Insight Matrix")
    with st.spinner("Calculating aggregate values via relational operations..."):
        ans_dataframe_df = pd.DataFrame()

        clean_text_pattern = r"^[a-zA-Z0-9\s\.,\-\'\&\!\(\)]+$"
        ans_dataframe_df = pd.read_sql_query(target_sql_statement, conn)

        if not ans_dataframe_df.empty:
            ans_dataframe_df = ans_dataframe_df.reset_index(drop=True)
            first_sort_col = ans_dataframe_df.columns[0]  # <-- Add [0] here
            try:
                ans_dataframe_df = ans_dataframe_df.sort_values(
                    by=first_sort_col, ascending=True, na_position="last", kind="mergesort"
                ).reset_index(drop=True)
            except Exception:
                ans_dataframe_df = ans_dataframe_df.sort_values(
                    by=first_sort_col, ascending=True, na_position="last"
                ).reset_index(drop=True)

            # Shift index to start at 1 instead of 0
            ans_dataframe_df.index = ans_dataframe_df.index + 1
            st.dataframe(ans_dataframe_df, use_container_width=True)

            fig = generate_plotly_chart(selected_question, ans_dataframe_df)
            # Display DataFrame and Plotly Chart side-by-side when a chart is generated
            if fig is not None:
                st.subheader("Data Visualization")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption(f"Total Rows Returned: {len(ans_dataframe_df)}")
                st.dataframe(ans_dataframe_df, use_container_width=True)
                st.info(
                    "This query returns a single summary value or text list, so it is best represented as a table above.")





