USE BonFoodTracker19
Go
-- eliminate dupe foods quickly with a new cte thingy i just learned...
-- http://www.sqlservertutorial.net/sql-server-basics/delete-duplicates-sql-server/
-- https://stackoverflow.com/questions/26908234/how-to-assign-cte-value-to-variable
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
SELECT Food_ID FROM cte
WHERE row_num > 1