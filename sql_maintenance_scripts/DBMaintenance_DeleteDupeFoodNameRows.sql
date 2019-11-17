USE BonFoodTracker19
GO
-- eliminate dupe foods quickly with a new cte thingy i just learned...
-- http://www.sqlservertutorial.net/sql-server-basics/delete-duplicates-sql-server/
-- https://stackoverflow.com/questions/26908234/how-to-assign-cte-value-to-variable
DROP TABLE #temp;
CREATE TABLE #temp(
	Food_ID int
);

WITH cte AS (
	SELECT Food_ID  AS Food_ID,
		ROW_NUMBER() OVER (
			PARTITION BY 
				FoodName
			ORDER BY 
				FoodName
		) row_num
		FROM Food
)
INSERT INTO #temp(Food_ID)
	SELECT Food_ID
	FROM cte
	WHERE row_num > 1


SELECT * from #temp

-- https://stackoverflow.com/questions/16481379/how-to-delete-using-inner-join-with-sql-server
DELETE s
FROM ServedAt s
JOIN #temp ON s.Food_ID = #temp.Food_ID

DELETE s2
FROM Serves s2
JOIN #temp ON s2.FoodID = #temp.Food_ID

DELETE f
FROM Food f
JOIN #temp ON f.Food_ID = #temp.Food_ID