-- International Debt Analysis SQL Queries
-- Assumes a normalized schema with the following tables:
-- countries(country_id, country_name, country_code)
-- indicators(indicator_id, series_name, series_code)
-- debt_data(country_id, indicator_id, year, debt_value)

-- 1. Retrieve all distinct country names
SELECT DISTINCT country_name
FROM countries
ORDER BY country_name;

-- 2. Count the total number of countries available
SELECT COUNT(*) AS total_countries
FROM countries;

-- 3. Find the total number of indicators present
SELECT COUNT(*) AS total_indicators
FROM indicators;

-- 4. Display the first 10 records of the dataset
SELECT *
FROM debt_data
LIMIT 10;

-- 5. Calculate the total global debt
SELECT SUM(debt_value) AS total_global_debt
FROM debt_data;

-- 6. List all unique indicator names
SELECT DISTINCT series_name
FROM indicators
ORDER BY series_name;

-- 7. Find the number of records for each country
SELECT c.country_name, COUNT(d.country_id) AS record_count
FROM countries c
LEFT JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY record_count DESC;

-- 8. Display all records where debt is greater than 1 billion USD
SELECT *
FROM debt_data
WHERE debt_value > 1000000000
ORDER BY debt_value DESC;

-- 9. Find minimum, maximum, and average debt values
SELECT MIN(debt_value) AS min_debt,
       MAX(debt_value) AS max_debt,
       AVG(debt_value) AS avg_debt
FROM debt_data;

-- 10. Count total number of records in the dataset
SELECT COUNT(*) AS total_records
FROM debt_data;

-- 11. Find the total debt for each country
SELECT c.country_name, SUM(d.debt_value) AS total_debt
FROM countries c
LEFT JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY total_debt DESC;

-- 12. Display the top 10 countries with highest total debt
SELECT c.country_name, SUM(d.debt_value) AS total_debt
FROM countries c
LEFT JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY total_debt DESC
LIMIT 10;

-- 13. Find the average debt per country
SELECT c.country_name, AVG(d.debt_value) AS avg_debt
FROM countries c
LEFT JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY avg_debt DESC;

-- 14. Calculate total debt for each indicator
SELECT i.series_name, SUM(d.debt_value) AS total_debt
FROM indicators i
LEFT JOIN debt_data d ON d.indicator_id = i.indicator_id
GROUP BY i.series_name
ORDER BY total_debt DESC;

-- 15. Identify the indicator contributing the highest total debt
SELECT i.series_name, SUM(d.debt_value) AS total_debt
FROM indicators i
JOIN debt_data d ON d.indicator_id = i.indicator_id
GROUP BY i.series_name
ORDER BY total_debt DESC
LIMIT 1;

-- 16. Find the country with the lowest total debt
SELECT c.country_name, SUM(d.debt_value) AS total_debt
FROM countries c
LEFT JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY total_debt ASC
LIMIT 1;

-- 17. Calculate total debt for each country and indicator combination
SELECT c.country_name, i.series_name, SUM(d.debt_value) AS total_debt
FROM countries c
JOIN debt_data d ON d.country_id = c.country_id
JOIN indicators i ON i.indicator_id = d.indicator_id
GROUP BY c.country_name, i.series_name
ORDER BY total_debt DESC;

-- 18. Count how many indicators each country has
SELECT c.country_name, COUNT(DISTINCT d.indicator_id) AS indicator_count
FROM countries c
LEFT JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY indicator_count DESC;

-- 19. Display countries whose total debt is above the global average
SELECT c.country_name, SUM(d.debt_value) AS total_debt
FROM countries c
JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
HAVING SUM(d.debt_value) > (SELECT AVG(total_debt) FROM (
    SELECT SUM(debt_value) AS total_debt
    FROM debt_data
    GROUP BY country_id
) subquery)
ORDER BY total_debt DESC;

-- 20. Rank countries based on total debt (highest to lowest)
SELECT c.country_name,
       SUM(d.debt_value) AS total_debt,
       RANK() OVER (ORDER BY SUM(d.debt_value) DESC) AS debt_rank
FROM countries c
JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY debt_rank;

-- 21. Find the top 5 indicators contributing most to global debt
SELECT i.series_name, SUM(d.debt_value) AS total_debt
FROM indicators i
JOIN debt_data d ON d.indicator_id = i.indicator_id
GROUP BY i.series_name
ORDER BY total_debt DESC
LIMIT 5;

-- 22. Calculate percentage contribution of each country to total global debt
SELECT c.country_name,
       SUM(d.debt_value) AS total_debt,
       (SUM(d.debt_value) / (SELECT SUM(debt_value) FROM debt_data)) * 100 AS percentage_of_global_debt
FROM countries c
JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY percentage_of_global_debt DESC;

-- 23. Identify the top 3 countries for each indicator based on debt
WITH ranked AS (
    SELECT i.series_name,
           c.country_name,
           SUM(d.debt_value) AS total_debt,
           ROW_NUMBER() OVER (PARTITION BY i.series_name ORDER BY SUM(d.debt_value) DESC) AS rn
    FROM indicators i
    JOIN debt_data d ON d.indicator_id = i.indicator_id
    JOIN countries c ON c.country_id = d.country_id
    GROUP BY i.series_name, c.country_name
)
SELECT series_name, country_name, total_debt
FROM ranked
WHERE rn <= 3
ORDER BY series_name, rn;

-- 24. Find the difference between maximum and minimum debt for each country
SELECT c.country_name,
       MAX(d.debt_value) - MIN(d.debt_value) AS debt_range
FROM countries c
JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY debt_range DESC;

-- 25. Create a view for the top 10 countries with highest debt
CREATE VIEW top_10_debt_countries AS
SELECT c.country_name, SUM(d.debt_value) AS total_debt
FROM countries c
JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY total_debt DESC
LIMIT 10;

SELECT * FROM top_10_debt_countries;

-- 26. Categorize countries into High Debt, Medium Debt, and Low Debt
WITH country_totals AS (
    SELECT c.country_name,
           SUM(d.debt_value) AS total_debt,
           AVG(SUM(d.debt_value)) OVER () AS avg_total_debt
    FROM countries c
    JOIN debt_data d ON d.country_id = c.country_id
    GROUP BY c.country_name
)
SELECT country_name, total_debt,
       CASE
           WHEN total_debt > avg_total_debt * 1.5 THEN 'High Debt'
           WHEN total_debt > avg_total_debt * 0.75 THEN 'Medium Debt'
           ELSE 'Low Debt'
       END AS debt_category
FROM country_totals
ORDER BY total_debt DESC;

-- 27. Use window functions to calculate cumulative debt per country
SELECT c.country_name,
       d.year,
       d.debt_value,
       SUM(d.debt_value) OVER (PARTITION BY c.country_name ORDER BY d.year) AS cumulative_debt
FROM countries c
JOIN debt_data d ON d.country_id = c.country_id
ORDER BY c.country_name, d.year;

-- 28. Find indicators where average debt is higher than overall average debt
SELECT i.series_name, AVG(d.debt_value) AS avg_debt
FROM indicators i
JOIN debt_data d ON d.indicator_id = i.indicator_id
GROUP BY i.series_name
HAVING AVG(d.debt_value) > (SELECT AVG(debt_value) FROM debt_data)
ORDER BY avg_debt DESC;

-- 29. Identify countries contributing more than 5% of global debt
WITH country_totals AS (
    SELECT c.country_name,
           SUM(d.debt_value) AS total_debt,
           (SELECT SUM(debt_value) FROM debt_data) AS global_debt
    FROM countries c
    JOIN debt_data d ON d.country_id = c.country_id
    GROUP BY c.country_name
)
SELECT country_name, total_debt,
       (total_debt / global_debt) * 100 AS contribution_pct
FROM country_totals
WHERE (total_debt / global_debt) * 100 > 5
ORDER BY contribution_pct DESC;

-- 30. Find the most dominant indicator for each country
WITH indicator_rank AS (
    SELECT c.country_name,
           i.series_name,
           SUM(d.debt_value) AS total_debt,
           ROW_NUMBER() OVER (PARTITION BY c.country_name ORDER BY SUM(d.debt_value) DESC) AS rn
    FROM countries c
    JOIN debt_data d ON d.country_id = c.country_id
    JOIN indicators i ON i.indicator_id = d.indicator_id
    GROUP BY c.country_name, i.series_name
)
SELECT country_name, series_name, total_debt
FROM indicator_rank
WHERE rn = 1
ORDER BY total_debt DESC;
