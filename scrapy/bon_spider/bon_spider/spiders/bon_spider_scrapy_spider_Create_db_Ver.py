# -*- coding: utf-8 -*-
import datetime
import json
import re # regex ftw!
import multiprocessing
import time

import pyodbc # for ODBC
import random # for random picking
import scrapy
import spoonacular # for spoonacular api.

# https://stackoverflow.com/a/316253
#from decimal import Decimal

# NOTE: if RUN_CREATE_DATABASE_SCRIPT is set to False, note that NEW_DB_NAME will still be used to populate data to the database with that name
NEW_DB_NAME = 'bonfoodtracker_test2'
# NOTE: The bon19 and master_access_username user has to be created on your instance of SQL server by a database admin. This script will NOT create this for you.
# Also, the master_access_username user MUST have access to creating databases, but not users, for maximum security.
BON19_USER_PASSWORD = '<user password here>'

BORKED_STRING = '\n\t\t\t'

TODAY_WEEKDAY = datetime.date.today().weekday()
TODAY_STRFTIME = datetime.datetime.now().strftime('%Y-%m-%d')

# For the final 333 "one-click" showcase with:
# the create database script
# if set to False, note that NEW_DB_NAME will still be used to populate data to the database with that name
RUN_CREATE_DATABASE_SCRIPT = True
# forced Spoonacular API calls
UNCONDITIONAL_SECONDARY_PROCESSING = True


# hacky workaround for saturday and sunday brunch/dinner.
MEAL_PERIODS = []
if TODAY_WEEKDAY == 5:
    MEAL_PERIODS = ['Brunch']
elif TODAY_WEEKDAY == 6:
    MEAL_PERIODS = ['Brunch', 'Dinner']
else:
    MEAL_PERIODS = ['Breakfast', 'Lunch', 'Dinner']

# for testing only, if you do in a cmd prmpt window/terminal:
# python bon_spider_scrapy_spider_Create_db_Ver.py
# rather than run it with: scrapy crawl bon_spider_scrapy_spider_create_db
# https://stackoverflow.com/questions/419163/what-does-if-name-main-do
if __name__ == 'main':
    print('[i][DEBUG] TESTING DB CONNECTION ONLY. NOT INSERTING ANYTHING.')
    # Test DB connection.
    db_conn = DatabaseConnection()
    db_conn.connect()
    #db_conn.insert_data()
    db_conn.close()

class CreateDatabaseConnection():
    ODBC_STRING = 'DRIVER={ODBC Driver 17 for SQL Server};\
        SERVER=server.com;\
        UID=master_access_username;PWD=pwd'
    CREATE_DB_SCRIPT = '''
-- Drop DB
IF DB_ID ('%s') IS NOT NULL
DROP DATABASE %s; -- this works to drop our database, but doing it from the gui doesn't work. verrry weird.

-- Create DB
CREATE DATABASE %s
ON PRIMARY(Name = '%s',
    FileName = 'E:\Database\MSSQL12.MSSQLSERVER\MSSQL\DATA\%s.mdf',
    Size=10MB,
    -- use 2 percents because Python tries to interpret percent and , as a formatted string
    FileGrowth=10%%,
    MaxSize=50MB
)
LOG ON(Name = '%s-log',
    FileName = 'E:\Database\MSSQL12.MSSQLSERVER\MSSQL\DATA\%s.ldf',
    Size=8MB,
    FileGrowth=15%%,
    MaxSize=60MB
);
''' % (NEW_DB_NAME, NEW_DB_NAME, NEW_DB_NAME, NEW_DB_NAME, NEW_DB_NAME, NEW_DB_NAME, NEW_DB_NAME)

    CREATE_TABLES_SCRIPT = '''
-- Create tables/constraints

-- Nutrition
CREATE TABLE Nutrition(
    NutritionID INT IDENTITY(1,1),
    -- The Bon provides all of this information
    -- The Bon always gives serving size info in
    -- ounces (oz) -- never in grams (g), with 1 digit of precision
    ServingSize DECIMAL(4, 1) NOT NULL,
    Calories SMALLINT NOT NULL,
    -- The Bon usually provides just 1 digit of precision for fat.
    Fat DECIMAL(4, 1) NOT NULL,
    Carbohydrates SMALLINT NOT NULL,
    Protein SMALLINT NOT NULL,
    -- Primary key constraints
    PRIMARY KEY(NutritionID),
    -- Domain constraints
    -- Note: We should reject bad nutrition information
    -- Sometimes the Bon has glitched in the past
    -- by including too many grams of fat/protein, so it's better to
    -- not include it rather than allow glitchy data
    CHECK(ServingSize > 0),
    CHECK(Fat >= 0 AND Fat <= 100),
    CHECK(Carbohydrates >= 0 AND Carbohydrates <= 200),
    CHECK(Protein >= 0 AND Protein <= 90),
);

-- Food
CREATE TABLE Food(
    Food_ID INT IDENTITY(1,1),
    -- 80 in nvarchar argument = 40 Unicode characters (yes, the Bon uses long food names)
    FoodName NVARCHAR(80) NOT NULL,
    -- "None", "Vegetarian", "Vegan", or "Made without Gluten-Containing Ingredients"
    Restrictions VARCHAR(42) NOT NULL,
    -- Most of our images will be <256 KB, so VARBINARY works efficiently:
    -- https://stackoverflow.com/questions/5613898/storing-images-in-sql-server
    -- (Recent versions of SQL server don't use the IMAGE datatype at all)
    -- Use some image API to get this information.
    Picture VARBINARY(max),
    -- Number of times this has been served in total
    Frequency INT NOT NULL,
    -- Use Spoonacular API to get this information
    -- 40 in nvarchar argument = 20 Unicode characters (yes, the Bon uses long food names)
    Cuisine NVARCHAR(40),
    -- PK constraints
    PRIMARY KEY(Food_ID),
    -- Domain constraints
    CHECK(Restrictions = 'None' OR Restrictions = 'Vegetarian' OR Restrictions = 'Vegan' OR Restrictions = 'Made without Gluten-Containing Ingredients'),
    CHECK(Frequency > 0)
);

 
Create Table Meal(
  MealDate date,
  MealPeriod varchar(9),
  VarietyScore float,
  primary key(MealDate, MealPeriod),
  CHECK(MealPeriod = 'Breakfast' OR MealPeriod = 'Lunch' OR MealPeriod = 'Dinner')
);

Create Table DBUser(
  Email varchar(127),
  UserPassword varchar(127) not null,
  primary key(email)
);

Create Table BonLocation(
  Location_ID int IDENTITY(1,1),
  Traffic varchar(15),
  LocationName varchar(63),
  primary key(location_ID),
  CHECK(Traffic = 'High' OR Traffic = 'Medium' OR Traffic = 'Low' OR Traffic = 'None')
);

-- RELATIONSHIP TABLES

Create Table ServedAt(
  Location_id int not null,
  food_id int not null,
  primary key(Location_id, food_id),
  constraint loc_fk_servedat foreign key (location_id) references BonLocation(Location_id),
  constraint food_fk_servedat foreign key (food_id) references food(food_id)
);
  
  
Create Table Has(
    NutritionID int not null,
    Food_ID int not null,
    primary key(Nutritionid, food_id),
  constraint Nutr_fk_has foreign key (Nutritionid) references Nutrition(Nutritionid),
  constraint food_fk_has foreign key (food_id) references food(food_id)
);

-- Serves
CREATE TABLE Serves(
    -- "Breakfast" or "Lunch" or "Dinner" (NOTE: This domain
    -- constraint should be enforced by the Meal entity)
    MealDate DATE NOT NULL,
    MealPeriod VARCHAR(9) NOT NULL,
    FoodID INT NOT NULL,
    FOREIGN KEY(MealDate, MealPeriod) REFERENCES Meal(MealDate, MealPeriod)
);

-- Rates
CREATE TABLE Rates(
    StarRating INT NOT NULL,
    Email VARCHAR(127) NOT NULL,
    Food_ID INT NOT NULL,
    PRIMARY KEY(Email, Food_ID),
    FOREIGN KEY(Email) REFERENCES DBUser(Email),
    FOREIGN KEY(Food_ID) REFERENCES Food(Food_ID),
    CHECK(StarRating >= 1 AND StarRating <= 5)
);

CREATE TABLE Pins(
    Email VARCHAR(127) NOT NULL,
    Food_ID INT NOT NULL,
    PRIMARY KEY(Email, Food_ID),
    FOREIGN KEY(Email) REFERENCES DBUser(Email),
    FOREIGN KEY(Food_ID) REFERENCES Food(Food_ID)
);

CREATE TABLE Eats(
    Email VARCHAR(127) NOT NULL,
    Food_ID INT NOT NULL,
    PRIMARY KEY(Email, Food_ID),
    FOREIGN KEY(Email) REFERENCES DBUser(Email),
    FOREIGN KEY(Food_ID) REFERENCES Food(Food_ID)
);
'''
           
# hmmm, currently, this "ginormous transaction of SPs" can't be done thanks to the sql interpreter being wonky...
# for now let's only do 1 stored procedure at a time, it's neater anyway
    CREATE_SPS_SCRIPTS = [
'''
CREATE PROCEDURE BonLocation_AddLocation
	@locationName varchar(63),
	@traffic varchar(15)
AS BEGIN
	-- Validate parameters
	IF (@locationName is null or @traffic is null) BEGIN
		RAISERROR('ERROR: location and traffic must not be null', 10, 0)
		RETURN 1
	END

	-- Existential checks

	-- create the location
	IF NOT EXISTS(SELECT LocationName FROM BonLocation WHERE LocationName = @locationName) BEGIN
		INSERT INTO BonLocation(LocationName, Traffic)
		VALUES (@locationName, @traffic)
	END
	-- update traffic (another prob to discuss in wk9 prob statement, traffic not updated across meals...)
	ELSE BEGIN
		PRINT('Location and traffic already exists. Updating current traffic and not adding a new location.')
		UPDATE BonLocation
		SET Traffic = @traffic
		WHERE locationName = @locationName;
	END

END''',
'''CREATE PROCEDURE [dbo].[BonLocation_UpdateTraffic]
	@location_id int,
	@traffic varchar(15)
AS BEGIN
	
	-- existential check
	IF (SELECT Location_ID FROM BonLocation WHERE Location_ID = @location_id) IS NULL BEGIN
		RAISERROR('ERROR:  Given location ID does not have a location assocaited with it.', 10, 0)
		RETURN 1
	END

	-- updating traffic
	UPDATE BonLocation
	set Traffic = @traffic
	WHERE Location_ID = @location_id;
END''',

'''CREATE PROCEDURE [dbo].[checkuserexists] @email varchar(127)
AS BEGIN
    select count(*) as num from DBUser where Email = @email
END''',
'''

CREATE PROCEDURE [dbo].[ComputeVarietyScores]
AS BEGIN

	-- iterate through all NULL variety scores
	-- https://support.microsoft.com/en-us/help/111401/how-to-iterate-through-a-result-set-by-using-transact-sql-in-sql-serve
	DECLARE @maxMD date, @maxMP varchar(9)
	-- this will use the prebuilt range search on the clustered index on the Meal table so it is very efficient to do this! :)
	SET @maxMD = (SELECT MAX(MealDate)
		FROM Meal
		WHERE VarietyScore IS NULL);
	SET @maxMP = (SELECT MAX(MealPeriod)
		FROM Meal
		WHERE VarietyScore IS NULL);

	WHILE @maxMD IS NOT NULL BEGIN
		-- iterate out by going backwards in meal periods first, then go backwards by meal date.
		WHILE @maxMP IS NOT NULL BEGIN
			-- iterate by food IDs!
			DECLARE @maxFID INT;
			SET @maxFID = (SELECT MAX(FoodID)
				FROM Serves
				WHERE MealDate = @maxMD AND MealPeriod = @maxMP)

			-- this is neat shorthand for DECLARE / SET!	
			DECLARE @CurrVS FLOAT = 10;

			WHILE @maxFID IS NOT NULL BEGIN
				DECLARE @currDay DATE = @maxMD;
				-- https://stackoverflow.com/a/1503495
				SET @currDay = dateadd(day, datediff(day, 1, @maxMD), 0)
				DECLARE @previousDaysChecked INT = 0;

				WHILE @previousDaysChecked < 5 BEGIN
					-- check if it occurs!
					-- (use count because checking NOT NULL could return multiple things which isn't allowed in this subquery with parentheses)
					IF (SELECT COUNT(FoodID) FROM Serves WHERE MealDate = @currDay AND MealPeriod = @maxMP AND FoodID = @maxFID) > 0 BEGIN
						IF @previousDaysChecked = 0 BEGIN
							SET @CurrVS = @CurrVS - 0.1;
						END
						ELSE IF @previousDaysChecked = 1 BEGIN
							SET @CurrVS = @CurrVS - 0.2;
						END
						ELSE IF @previousDaysChecked = 2 BEGIN
							SET @CurrVS = @CurrVS - 0.4;
						END
						ELSE IF @previousDaysChecked = 3 BEGIN
							SET @CurrVS = @CurrVS - 0.2;
						END
						ELSE IF @previousDaysChecked = 4 BEGIN
							SET @CurrVS = @CurrVS - 0.1;
						END
					END

					SET @currDay = dateadd(day, datediff(day, 1, @maxMD), 0)
					SET @previousDaysChecked = @previousDaysChecked + 1
				END

				-- [iterate]
				SET @maxFID = (SELECT MAX(FoodID)
					FROM Serves
					-- note the extra condition here
					WHERE MealDate = @maxMD AND MealPeriod = @maxMP AND FoodID < @maxFID)
			END

			-- Set the variety score!
			IF @CurrVS < 0 BEGIN
				UPDATE Meal
				SET VarietyScore = 0
				WHERE MealDate = @maxMD AND MealPeriod = @maxMP;
			END
			ELSE BEGIN
				UPDATE Meal
				SET VarietyScore = @CurrVS
				WHERE MealDate = @maxMD AND MealPeriod = @maxMP;
			END

			-- [iterate]
			-- previous meal period in the day
			SET @maxMP = (SELECT MAX(MealPeriod)
				FROM Meal
				-- note the extra condition here
				WHERE VarietyScore IS NULL AND MealPeriod < @maxMP);
		END
		SET @maxMD = (SELECT MAX(MealDate)
			FROM Meal
			-- note the extra condition here
			WHERE VarietyScore IS NULL AND MealDate < @maxMD);
		-- will break out of whole loop next run if there is no meal date, so don't need to worry about period being reset to max each time
		SET @maxMP = (SELECT MAX(MealPeriod)
			FROM Meal
			-- note the extra condition here
			WHERE VarietyScore IS NULL);
	END


END
''',
'''

CREATE PROCEDURE [dbo].[Eats_AddEats]
	-- all fields are required
	@DBUser_Email varchar(127),
	@Food_FoodName nvarchar(80) 
AS BEGIN
	declare @Food_FoodID int
	select @Food_FoodID = Food_ID from Food where FoodName = @Food_FoodName
	-- Validate parameters
	IF (SELECT Food_ID FROM Food WHERE Food_ID = @Food_FoodID) IS NULL BEGIN
		RAISERROR('ERROR: Food ID does not exist.', 10, 0)
		RETURN 1
	END
	ELSE IF (SELECT Email FROM DBUser WHERE Email = @DBUser_Email) IS NULL BEGIN
		RAISERROR('ERROR: DBUser with specified Email does not exist.', 10, 0)
		RETURN 2
	END 
	IF (SELECT Email FROM Eats WHERE Email = @DBUser_Email AND Food_ID = @Food_FoodID) IS NOT NULL BEGIN
		RAISERROR('ERROR: Pin already exists. Try deleting it first.', 10, 0)
		RETURN 4 -- this error code is useful for whatever code we use in the project
	END
	INSERT INTO Eats(Email, Food_ID)
	VALUES (@DBUser_Email, @Food_FoodID);
END
''',
'''

CREATE PROCEDURE [dbo].[Food_AddFoodEntry_WithLocAndMeal_ReducedForNow]
	@foodName nvarchar(80),
	@Restrictions varchar(42),
	@mealDate date,
	@mealPeriod varchar(9),
	@locationName varchar(63)
AS BEGIN
	-- Validate parameters
	IF (@foodName is null) BEGIN
		RAISERROR('ERROR: Foodname must not be null', 10, 0)
		RETURN 1
	END
	
	-- Existential check
	IF (SELECT MealDate FROM meal WHERE MealDate = @mealDate AND MealPeriod = @mealPeriod) IS  NULL BEGIN
		RAISERROR('ERROR: No meal associated with given meal date and period. Failed to add.', 10, 0)
		RETURN 2
	END
	declare @location_ID int;
	set @location_ID = (SELECT Location_ID  FROM  BonLocation WHERE LocationName = @locationName);
	IF @location_ID IS  NULL BEGIN
		RAISERROR('ERROR: No Location associated with given Location Name. Failed to add.', 10, 0)
		RETURN 4
	END
	-- create the Food entry
	-- dont insert in an ID, that is autogenerated
	-- if the Food entry already exists we can ignore adding another one, throwing an error would halt the web scraper
	-- which isn't ideal in my case...
	IF NOT EXISTS(SELECT FoodName FROM Food WHERE FoodName = @Foodname) BEGIN
		INSERT INTO Food(FoodName, Restrictions, Frequency)
		VALUES (@foodName, @Restrictions, 1);
	END
	ELSE
		UPDATE Food
		SET Frequency = Frequency + 1
		WHERE FoodName = @Foodname AND Restrictions = @Restrictions

	declare @Food_ID int;
	set @Food_ID = (SELECT Food_ID FROM Food WHERE FoodName = @foodName AND Restrictions = @Restrictions)

	-- Add Food -> Meal association
	IF NOT EXISTS(SELECT MealDate FROM Serves WHERE MealDate = @MealDate AND MealPeriod = @MealPeriod AND FoodID = @Food_ID) BEGIN
		INSERT INTO Serves(MealDate, MealPeriod, FoodID)
		VALUES (@mealDate, @mealPeriod, @Food_ID);
	END
	ELSE
		PRINT('Food and meal association already exist.')

	-- Add Food -> Location association
	IF NOT EXISTS(SELECT Location_id FROM ServedAt WHERE Location_ID = @Location_ID AND Food_ID = @Food_ID) BEGIN
		INSERT INTO ServedAt(Location_ID, food_id)
		VALUES (@location_ID, @Food_ID);
	END
	ELSE
		PRINT('Food and location association already exist.')

END
''',
'''
CREATE PROCEDURE [dbo].[Food_SecondaryProcessing_AddCuisineAndPicture]
	@foodName nvarchar(80),
	@cuisine nvarchar(40),
	@picture varbinary(max)
AS BEGIN
	-- Validate parameters
	IF (@foodName is null or @cuisine is null or @picture is null) BEGIN
		RAISERROR('ERROR: Foodname, cuisine, or picture all must not be null', 10, 0)
		RETURN 1
	END
	
	-- Existential check
	IF (SELECT Food_ID FROM Food WHERE FoodName = @foodName) IS NULL BEGIN
		RAISERROR('ERROR: Food ID doesn''t already exist in table. Failed to add.', 10, 0)
		RETURN 2
	END

	-- add cuisine and picture to food id
	UPDATE Food
	SET Cuisine = @cuisine, Picture = @picture
	WHERE Food_ID = (SELECT Food_ID FROM Food WHERE FoodName = @foodName);

END
''',
'''
CREATE PROCEDURE [dbo].[Food_SecondaryProcessing_AddPictureOnly]
	@foodName nvarchar(80),
	@picture varbinary(max)
AS BEGIN
	-- Validate parameters
	IF (@foodName is null or @picture is null) BEGIN
		RAISERROR('ERROR: Foodname or picture must not be null', 10, 0)
		RETURN 1
	END
	
	-- Existential check
	IF (SELECT Food_ID FROM Food WHERE FoodName = @foodName) IS NULL BEGIN
		RAISERROR('ERROR: Food ID doesn''t already exist in table. Failed to add.', 10, 0)
		RETURN 2
	END

	-- add cuisine and picture to food id
	UPDATE Food
	SET Picture = @picture
	WHERE Food_ID = (SELECT Food_ID FROM Food WHERE FoodName = @foodName);

END
''',
'''
CREATE PROCEDURE [dbo].[Food_SecondaryProcessing_DoesCuisineOrPictureExist]
	@foodName nvarchar(80)
AS BEGIN
	DECLARE @cuisine nvarchar(40) = (SELECT Cuisine FROM Food WHERE FoodName = @foodName)
	DECLARE @picture varbinary(max) = (SELECT Picture FROM Food WHERE FoodName = @foodName)
	IF @cuisine IS NOT NULL OR @picture IS NOT NULL BEGIN
		RETURN 1
	END
	RETURN 0

END
''',
'''
CREATE PROCEDURE [dbo].[Meals_Addmeal_fixed]
	@mealDate date,
	@mealPeriod varchar(9)
AS BEGIN
	-- Validate parameters
	IF (@mealDate is null or @mealPeriod is null) BEGIN
		RAISERROR('ERROR: meal and period must not be null', 10, 0)
		RETURN 1
	END
	ELSE IF (@mealPeriod != 'Breakfast' and @mealPeriod != 'Lunch' and @mealPeriod != 'Dinner') BEGIN
		RAISERROR('ERROR: Invalid Period.', 10, 0)
		RETURN 2
	END
	
	--create the meal if not already exists. (dont throw an error for web scraper test purposes/dont stop the program running etc)
	IF NOT EXISTS(SELECT MealDate FROM meal WHERE MealDate = @mealDate AND MealPeriod = @mealPeriod) BEGIN
		INSERT INTO Meal(MealDate, MealPeriod)
		VALUES (@mealDate, @mealPeriod);
	END
	ELSE
		PRINT('Meal with this date and period already exists. Not added')
END
''',
'''
CREATE PROCEDURE [dbo].[Nutrition_AddNutrition_fixed]
	@foodName nvarchar(80),
	-- we will convert floats to decimal(0,1) later on, because MOST python datatypes I tried won't automatically be 
	-- the 'decimal' datatype in SQL (float, Decimal "numeric", etc.).
	@servingSize float,
	@calories smallint,
	@fat float,
	@carbohydrates smallint,
	@protein smallint
AS BEGIN
	-- Validate parameters
	IF (@foodName is null
		or @servingSize is null 
		or @calories is null
		or @fat is null 
		or @carbohydrates is null 
		or @protein is null) BEGIN
		RAISERROR('ERROR: All parameters must not be null', 10, 0)
		RETURN 1
	END
	
	-- Existential check
	DECLARE @selectedFoodID int;
	SET @selectedFoodID = (SELECT Food_ID FROM Food WHERE FoodName = @foodName);
	IF @selectedFoodID IS NULL BEGIN
		RAISERROR('ERROR: No food entry associated with the given food name. Failed to add.', 10, 0)
		RETURN 2
	END

	-- Now add the nutrition information, if it does not exist yet (easier to do this rather than throw an error because of how
	-- the web scraper is intended to work, it won't catch these exceptions and stop the program in the middle of scraping
	-- (not ideal in the way it's written...), rather keep adding nutrition entries
	-- (which is what we want to do...)
	IF NOT EXISTS(SELECT NutritionID FROM Has WHERE Food_ID = @selectedFoodID) BEGIN
		DECLARE @insertedNutritionID table(NutritionID int);
		DECLARE @selectedNutritionID int;

		INSERT INTO Nutrition(ServingSize, Calories, Fat, Carbohydrates, Protein)
		-- https://www.mssqltips.com/sqlservertip/2183/using-insert-output-in-a-sql-server-transaction/
		OUTPUT inserted.NutritionID INTO @insertedNutritionID
		-- also convert fat / protein from float -> decimal
		VALUES (@servingSize, @calories, CONVERT(decimal(4,1), @fat), @carbohydrates, convert(decimal(4,1), @protein));

		-- Now associate food -> nutrition information
		SET @selectedNutritionID = (SELECT NutritionID FROM @insertedNutritionID);
		
		INSERT INTO Has(NutritionID, Food_ID)
		VALUES (@selectedNutritionID, @selectedFoodID);
	END


END
''',
'''

CREATE PROCEDURE [dbo].[Pins_AddPin]
	-- all fields are required
	@DBUser_Email varchar(127),
	@Food_FoodName nvarchar(80) 
AS BEGIN
	declare @Food_FoodID int
	select @Food_FoodID = Food_ID from Food where FoodName = @Food_FoodName
	-- Validate parameters
	IF (SELECT Food_ID FROM Food WHERE Food_ID = @Food_FoodID) IS NULL BEGIN
		RAISERROR('ERROR: Food ID does not exist.', 10, 0)
		RETURN 1
	END
	ELSE IF (SELECT Email FROM DBUser WHERE Email = @DBUser_Email) IS NULL BEGIN
		RAISERROR('ERROR: DBUser with specified Email does not exist.', 10, 0)
		RETURN 2
	END 
	-- Now check to see if the pin DOES exist.
	IF (SELECT Email FROM Pins WHERE Email = @DBUser_Email AND Food_ID = @Food_FoodID) IS NOT NULL BEGIN
		RAISERROR('ERROR: Pin already exists. Try deleting it first.', 10, 0)
		RETURN 4 -- this error code is useful for whatever code we use in the project
	END
	-- If it DOES already, delete the pin!
	INSERT INTO Pins(Email, Food_ID)
	VALUES (@DBUser_Email, @Food_FoodID);
END
''',
'''
CREATE PROCEDURE [dbo].[Pins_DeletePin]
	@email varchar(127),
	@Food_ID int
AS BEGIN
	
	-- existential checks
	IF (SELECT Email FROM Pins WHERE Email = @email and @Food_ID = Food_ID) IS NULL BEGIN
		RAISERROR('ERROR:  Given foodID and email doesnt have a pin associated with it.', 10, 0)
		RETURN 1
	END

	-- updating traffic
	DELETE FROM Pins
	WHERE  Email = @email and @Food_ID = Food_ID;
END
''',
'''

CREATE PROCEDURE [dbo].[Rates_AddRating]
	-- all fields are required
	@DBUser_Email varchar(127),
	@Food_Name nvarchar(80),
	@Rates_StarRating int
AS BEGIN
	declare @Food_FoodID int;
	Select @Food_FoodID = Food.Food_ID  from Food where FoodName = @Food_Name;
	-- Validate parameters
	IF (@Rates_StarRating < 1 or @Rates_StarRating > 5) BEGIN
		RAISERROR('ERROR: Invalid star rating (must be between 1 and 5).', 10, 0)
		RETURN 1
	END
	ELSE IF (SELECT FoodName FROM Food WHERE FoodName = @Food_Name) IS NULL BEGIN
		RAISERROR('ERROR: Food Name does not exist.', 10, 0)
		RETURN 2
	END
	ELSE IF (SELECT Email FROM DBUser WHERE Email = @DBUser_Email) IS NULL BEGIN
		RAISERROR('ERROR: DBUser with specified Email does not exist.', 10, 0)
		RETURN 3
	END 
	-- Now check to see if the rating already exists.
	IF (SELECT StarRating FROM Rates WHERE Email = @DBUser_Email AND Food_ID = @Food_FoodID) IS NOT NULL BEGIN
		RAISERROR('ERROR: Rating already exists. Please update or delete it.', 10, 0)
		RETURN 4 -- this error code is useful for whatever code we use in the project
	END
	-- If not, create the rating!
	INSERT INTO Rates(Email, Food_ID, StarRating)
	VALUES (@DBUser_Email, @Food_FoodID, @Rates_StarRating);
END
''',
'''

CREATE PROCEDURE [dbo].[Rates_DeleteRating]
	-- all fields are required
	@DBUser_Email varchar(127),
	@Food_FoodID int
AS BEGIN
	-- Validate parameters
	IF (SELECT Food_ID FROM Food WHERE Food_ID = @Food_FoodID) IS NULL BEGIN
		RAISERROR('ERROR: Food ID does not exist.', 10, 0)
		RETURN 1
	END
	ELSE IF (SELECT Email FROM DBUser WHERE Email = @DBUser_Email) IS NULL BEGIN
		RAISERROR('ERROR: DBUser with specified Email does not exist.', 10, 0)
		RETURN 2
	END 
	-- Now check to see if the rating DOES NOT exist.
	IF (SELECT StarRating FROM Rates WHERE Email = @DBUser_Email AND Food_ID = @Food_FoodID) IS NULL BEGIN
		RAISERROR('ERROR: Rating does not exist yet. Therefore, it cannot be deleted if it is not created first (try creating it).', 10, 0)
		RETURN 4 -- this error code is useful for whatever code we use in the project
	END
	-- If it DOES exist already, delete the rating!
	DELETE FROM Rates
	WHERE Email = @DBUser_Email AND Food_ID = @Food_FoodID;
END
''',
'''


CREATE PROCEDURE [dbo].[Rates_UpdateRating]
	-- all fields are required
	@DBUser_Email varchar(127),
	@Food_FoodID int,
	-- here, we provide the new star rating
	@Rates_StarRating int
AS BEGIN
	-- Validate parameters
	IF (@Rates_StarRating < 1 or @Rates_StarRating > 5) BEGIN
		RAISERROR('ERROR: Invalid star rating (must be between 1 and 5).', 10, 0)
		RETURN 1
	END
	ELSE IF (SELECT Food_ID FROM Food WHERE Food_ID = @Food_FoodID) IS NULL BEGIN
		RAISERROR('ERROR: Food ID does not exist.', 10, 0)
		RETURN 2
	END
	ELSE IF (SELECT Email FROM DBUser WHERE Email = @DBUser_Email) IS NULL BEGIN
		RAISERROR('ERROR: DBUser with specified Email does not exist.', 10, 0)
		RETURN 3
	END 
	-- Now check to see if the rating DOES NOT exist.
	IF (SELECT StarRating FROM Rates WHERE Email = @DBUser_Email AND Food_ID = @Food_FoodID) IS NULL BEGIN
		RAISERROR('ERROR: Rating does not exist yet. Please create it first.', 10, 0)
		RETURN 4 -- this error code is useful for whatever code we use in the project
	END
	-- If it DOES exist already, update the rating!
	UPDATE Rates
	SET StarRating = @Rates_StarRating
	WHERE Email = @DBUser_Email AND Food_ID = @Food_FoodID;
END
''',
'''
CREATE PROCEDURE [dbo].[searchfood]  @date date, @meal varchar(9), @search varchar(63)
AS

IF not exists (SELECT meal.MealDate FROM Meal WHERE MealDate = @date) BEGIN
		RAISERROR('ERROR: No foods entered for that date exist.', 10, 0)
		RETURN 1
	END 
else IF not exists (SELECT MealPeriod FROM Meal WHERE MealPeriod = @meal) BEGIN
		RAISERROR('ERROR: You have entered an improper meal period.', 10, 0)
		RETURN 2
	END 
SELECT Food.FoodName 
FROM Food, Serves  
WHERE Serves.MealDate = @date and 
food.Food_ID =Serves.FoodID and MealPeriod = @meal and 
FoodName like @search group by FoodName;
''',
'''

CREATE PROCEDURE [dbo].[Serves_AddAssocFoodAndMeal]
	@foodName varchar(80),
	@mealDate date,
	@mealPeriod varchar(9)
AS BEGIN
	-- Validate parameters
	IF (@mealDate is null or @mealPeriod is null) BEGIN
		RAISERROR('ERROR: meal and period must not be null', 10, 0)
		RETURN 1
	END
	ELSE IF (@mealPeriod != 'Breakfast' or @mealPeriod != 'Lunch' or @mealPeriod != 'Dinner') BEGIN
		RAISERROR('ERROR: Invalid Period.', 10, 0)
		RETURN 2
	END

	-- Existential checks
	IF (SELECT MealDate FROM Meal WHERE MealDate = @mealDate AND MealPeriod = @mealPeriod) IS NULL BEGIN
		RAISERROR('ERROR: Meal with this date and period does not exist. Cannot add food/meal.', 10, 0)
		RETURN 3
	END

	DECLARE @foodID int;
	SET @foodID = (SELECT Food_ID FROM Food WHERE FoodName = @foodName);

	IF @foodID IS NULL BEGIN
		RAISERROR('ERROR: Food with this name does not exist. Cannot add food/meal.', 10, 0)
		RETURN 3
	END
	--create the food/meal combo
	INSERT INTO Serves(MealDate, MealPeriod, FoodID)
	VALUES (@mealDate, @mealPeriod, @foodID);
END
''',
'''

CREATE Procedure [dbo].[userLogin] @email varchar(127), @pass varchar(127)
as
select count(*) as num from DBUser where @email = Email and @pass = UserPassword;

''',
'''

CREATE Procedure [dbo].[userRegistration] @email varchar(127), @pass varchar(127)
as

if (@email is not null and @pass is not null) and not exists(select email from DBUser where @email = Email) 
insert into DBUser (Email, UserPassword)
values(@email, @pass);
else RAISERROR('ERROR: Registration Unsucessful, Null value entered or username is already in use.', 10, 0)
		RETURN 1
''',
'''
        
CREATE Procedure [dbo].[ViewEats]
@email varchar(127)
as 
begin
IF (SELECT Email FROM DBUser WHERE Email = @email) IS NULL BEGIN
		RAISERROR('ERROR: DBUser with specified Email does not exist.', 10, 0)
		RETURN 1
	END 

select foodname 
from Food
inner join Eats on Food.Food_ID = Eats.Food_ID
inner join DBUser on Eats.Email = DBUser.Email
where DBUser.Email = @email;
end;
''',
'''

CREATE Procedure [dbo].[ViewPinned] 
@date date,
@email varchar(127)
as 
begin
IF (SELECT Email FROM DBUser WHERE Email = @email) IS NULL BEGIN
		RAISERROR('ERROR: DBUser with specified Email does not exist.', 10, 0)
		RETURN 1
	END 

select foodname 
from Food
inner join Pins on Food.Food_ID = Pins.Food_ID
inner join DBUser on pins.Email = DBUser.Email
inner join Serves on Food.Food_ID = Serves.FoodID
where DBUser.Email = @email and Serves.MealDate = @date
group by FoodName;
end;
''',
'''
CREATE procedure [dbo].[BinaryFromName] @FoodName nvarchar(80) 
as 

IF not exists (SELECT food.Food_ID FROM Food WHERE Food.FoodName = @FoodName) BEGIN
		RAISERROR('ERROR: No foods with that name exist.', 10, 0)
		RETURN 1
	END 

select food.Picture
from Food
where food.FoodName = @FoodName
''',
'''
CREATE Procedure [dbo].[viewrating]
as
select FoodName, AVG(Rates.StarRating) as Rating, COUNT(FoodName) as [Rating Number]
from Food
inner join  Rates on Rates.Food_ID = food.Food_ID
group by FoodName;
''']

    
    CREATE_USER_SCRIPT = '''
-- Add existing bon19 login to the database
-- A login is for the whole DBMS server, a user is for a specific database
-- https://stackoverflow.com/questions/1134319/difference-between-a-user-and-a-login-in-sql-server
-- https://docs.microsoft.com/en-us/sql/relational-databases/security/authentication-access/create-a-database-user?view=sql-server-ver15#TsqlProcedure
CREATE USER [bon19] FOR LOGIN [bon19]; -- it will have the same password as the bon19 we currently use

-- Grant permissions
GRANT EXECUTE ON BonLocation_AddLocation TO bon19;
GRANT EXECUTE ON [BonLocation_UpdateTraffic] TO bon19;
GRANT EXECUTE ON [ComputeVarietyScores] to bon19;
GRANT EXECUTE ON [Eats_AddEats] to bon19;
GRANT EXECUTE ON Food_AddFoodEntry_WithLocAndMeal_ReducedForNow TO bon19;
GRANT EXECUTE ON [Food_SecondaryProcessing_AddCuisineAndPicture] to bon19;
GRANT EXECUTE ON [Food_SecondaryProcessing_AddPictureOnly] to bon19;
GRANT EXECUTE ON [Food_SecondaryProcessing_DoesCuisineOrPictureExist] to bon19;

GRANT EXECUTE ON Meals_Addmeal_fixed TO bon19;
GRANT EXECUTE ON [Nutrition_AddNutrition_fixed] TO bon19;
GRANT EXECUTE ON Pins_AddPin TO bon19;
GRANT EXECUTE ON Pins_DeletePin TO bon19;
GRANT EXECUTE ON Rates_AddRating TO bon19;
GRANT EXECUTE ON Rates_DeleteRating TO bon19;
GRANT EXECUTE ON Rates_UpdateRating TO bon19;
GRANT EXECUTE ON searchfood TO bon19;
GRANT EXECUTE ON Serves_AddAssocFoodAndMeal TO bon19;
GRANT EXECUTE ON userLogin TO bon19;
GRANT EXECUTE ON userRegistration TO bon19;
GRANT EXECUTE ON ViewEats TO bon19;
GRANT EXECUTE ON ViewPinned TO bon19;

-- give permission to read/write data
EXEC sp_addrolemember 'db_datareader', 'bon19';
EXEC sp_addrolemember 'db_datawriter', 'bon19';
    '''
    
    def connect(self):
        # autocommit=True fixes the annoying multiple statements error
        # for creating the DB now as it thinks it's multiple statements, we can turn it off later
        # https://github.com/mkleehammer/pyodbc/issues/149#issuecomment-255154981
        self.conn = pyodbc.connect(self.ODBC_STRING, autocommit=True)
        self.cursor = self.conn.cursor()
    
    def create_database(self):
        self.cursor.execute('USE master;') # need to do this before first part
        self.cursor.commit() # here we need to do a "virtual GO", since we aren't in SQL server to
                        # "remove the current transaction to make it a not multi stage transaction"
                        # to prevent an SQL error. Then we can create the DB.
        
        print('[i] CONSTRUCTING THE DB.')
        self.cursor.execute(self.CREATE_DB_SCRIPT)
        self.cursor.commit() # actually create the DB before tables etc. so we have it in the master server before running next part
        
        # turn off autocommit for the create table, SP, etc statements, since SQL won't complain anymore
        self.conn.autocommit = False
        
        self.cursor.execute('USE %s;' % NEW_DB_NAME) # need to do this before second, third, etc. parts
        self.cursor.commit() # here we need to do a "virtual GO"
        
        # do tables/SPs/users separately since sql will complain about create/alter procedure not being 1st in the batch stuff
        print('[i] ADDING TABLES.')
        self.cursor.execute(self.CREATE_TABLES_SCRIPT)
        self.cursor.commit() # actually create the DB this time so we have it in the master server now

        print('[i] ADDING SPs.')
        for sp_script in self.CREATE_SPS_SCRIPTS:
            self.cursor.execute(sp_script)
            self.cursor.commit()

        print('[i] ADDING bon19 USER.')
        self.cursor.execute(self.CREATE_USER_SCRIPT)
        self.cursor.commit()


    def close(self):
        print('[i] CLOSING DB CONNECTION.')
        self.cursor.close()
        self.conn.close()

    

class DatabaseConnection():
    ODBC_STRING = 'DRIVER={ODBC Driver 17 for SQL Server};\
        SERVER=server.com;DATABASE=%s;\
        UID=bon19;PWD=%s' % (NEW_DB_NAME, BON19_USER_PASSWORD)
    SPOONACULAR_API_KEY = '<API key here>'

    def __init__(self):
        self.sp_api = spoonacular.API(self.SPOONACULAR_API_KEY)
        
    def connect(self):
        self.conn = pyodbc.connect(self.ODBC_STRING)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('USE %s;' % NEW_DB_NAME)
        self.cursor.commit() # here we need to do another "virtual GO" just in case

    def close(self):
        print('[i] CLOSING DB CONNECTION.')
        self.cursor.close()
        self.conn.close()
    
    def insert_locs(self, meal_options):
       # this is bad python programming practice but i got no time to spare
        meal_period_index = 0
        type_index = 0
        for meal_type_options in meal_options:
            locs = []
                        
            for meal_period_items in meal_type_options:
                if type_index == 0:
                    pass
                elif type_index == 1:
                    for location_list in meal_period_items:
                        # all locations for a particular meal,
                        # ordered by meal item...
                        locs.append(location_list)    
                elif type_index >= 2:
                    break
                
                meal_period_index = meal_period_index + 1
            
            # ... and locs (is not empty)
            if type_index == 1 and locs:
                # (only add them to DB when type_index == 1)
                # get unique locations then add them to DB
                # DO NOT ADD VALUE FOR IDENTITY COLUMN (that is automatically done)!
                # list(set(...)) = unique list
                for loc in list(set(locs)):
                    # Fake data for traffic for now...
                    random_traffic = random.choice(['Low', 'Medium', 'High'])
                    
                    # https://github.com/mkleehammer/pyodbc/wiki/Calling-Stored-Procedures
                    # except for me, {CALL ...} syntax isn't reliable, probably due to pyodbc being somewhat broken
                    # or MS SQL being weird (thanks Microsoft...) so I'm using the good old MS SQL exec.
                    # https://stackoverflow.com/a/28636308
                    # ^ that's not even the right syntax for MS SQL but it's the right idea. some further tweaking will fix it
                    self.cursor.execute(
                        'EXEC [BonLocation_AddLocation] ?,?',
                        loc,
                        random_traffic
                    )
                    # we still must do a .commit(), even with SPs...
                    # https://stackoverflow.com/a/14826066
                    self.cursor.commit()
                
            meal_period_index = 0
            type_index = type_index + 1

    def insert_nutrition_infos(self, meal_options):
        pass


    def insert_loc_food_meal_assocs(self, meal_options):
        food_index = 0
        meal_index = 0
        foods = meal_options[0]
        nutrition_infos = meal_options[2]
        restrictions = meal_options[3]

        for meal_locs in meal_options[1]:
            # add meal locations for a particular period,
            # associated with a particular food...
            
            # for Frequency as a computed column, get the count of the item
            # once we put it in the table.            
            for food_meal_loc in meal_locs:
                # TODO do we need TRY/EXCEPT if food already exists?
                food_name = foods[meal_index][food_index]
                #print(len(restrictions[meal_index]))
                #print(len(foods[meal_index]))
                #print(restrictions[meal_index][food_index])
                food_restrictions = restrictions[meal_index][food_index]
                #print(food_restrictions)
                meal_date = TODAY_STRFTIME
                meal_period = MEAL_PERIODS[meal_index]
                
                self.cursor.execute(
                    'EXEC [Food_AddFoodEntry_WithLocAndMeal_ReducedForNow] ?,?,?,?,?',
                    food_name,
                    food_restrictions,
                    meal_date,
                    meal_period,
                    food_meal_loc
                )
                # we still must do a .commit(), even with SPs...
                self.cursor.commit()
                
                # now add its nutrition info, if it exists.
                if nutrition_infos[meal_index][food_index]:
                    nutrition_info_entry = nutrition_infos[meal_index][food_index]
                    # debug bad serving size entries (thanks bone)
                    # because everything has to have some serving size (it exists) at the very least.
                    final_serving_size = nutrition_info_entry[1] if nutrition_info_entry[1] > 0 else 0.1
                    
                    # don't include bad data (> 100 g fat, > 200 g carbohydrates, > 90 g protein (these are DB constraints), etc)
                    # (if this happens, this is just a Bone "glitch" and so what's the point of including it in the DB anyway.)
                    if nutrition_info_entry[3] <= 100.0 and nutrition_info_entry[4] <= 200 and nutrition_info_entry[5] <= 90.0:
                        self.cursor.execute(
                        'EXEC [Nutrition_AddNutrition_fixed] ?,?,?,?,?,?',
                            food_name,
                            final_serving_size,
                            nutrition_info_entry[2],
                            nutrition_info_entry[3],
                            nutrition_info_entry[4],
                            nutrition_info_entry[5]
                        )
                        self.cursor.commit()
                    else:
                        print('[Additional Info] Bone might''ve did an oopsie! Their menu nutrition probably glitched, so we are not adding nutrition info for a menu item with:')
                        print('Serving Size: %.1f, Calories: %d, Fat: %.1f, Carbs: %d, Protein: %.1f' %
                            (final_serving_size,
                            nutrition_info_entry[2],
                            nutrition_info_entry[3],
                            nutrition_info_entry[4],
                            nutrition_info_entry[5])
                        )
                
                food_index += 1
                
    
            food_index = 0
            meal_index = meal_index + 1
    
    def insert_meals(self):
        for meal_period in MEAL_PERIODS:
            # TODO: make the Meals_Addmeal_fixed SP build the variety score.
            self.cursor.execute(
                'EXEC [Meals_Addmeal_fixed] ?,?',
                datetime.datetime.now(),
                meal_period
            )
            # we still must do a .commit(), even with SPs...
            self.cursor.commit()

    # Only do this after data was successfully imported since API calls are expensive!
    def secondary_processing_cuisines_pics(self, meal_options):
        for food_period_options in meal_options[0]:
            for food_name in food_period_options:
                # skip re-fetching from api if cuisine or picture are already added to avoid wasting api calls.
                self.cursor.execute(
                    # NOTE, unfortunately, in pyodbc, we have to use a separate DECLARE/SELECT statement after EXEC JUST to get the return value.
                    # https://github.com/mkleehammer/pyodbc/wiki/Calling-Stored-Procedures#output-parameters-and-return-values
                    # DO NOT WORRY. This does not execute any raw SQL on the database, it merely gets the return value.
                    # In the future, I would have picked a different library for Python ODBC connections,
                    # I did not anticipate this workaround to have to happen.
                    'DECLARE @ret INT;\
                    EXEC @ret = [Food_SecondaryProcessing_DoesCuisineOrPictureExist] ?;\
                    SELECT @ret AS does_cuisine_or_pic_exist;',
                    food_name
                )
                does_cuisine_or_pic_exist = self.cursor.fetchval()
                
                if does_cuisine_or_pic_exist == 0:
                   # dupe the ingredient/food option b/c we don't care...
                   cuisine_json = self.sp_api.classify_cuisine(food_name, food_name).json()
                   cuisine = cuisine_json.get('cuisine') # it can be empty value for cuisine too
                    
                   pic_args = {'ingredients': food_name, 'limitLicense': True, 'number': '1', 'ranking': '1'}
                   # https://stackoverflow.com/questions/30229231/python-save-image-from-url/30229298
                   import requests
                   # for testing/debugging...
                   #result = self.sp_api.search_recipes_by_ingredients(**pic_args).json()
                   #import ipdb; ipdb.set_trace()
                   # get an image if possible... else don't worry about importing it...
                   sp_json = self.sp_api.search_recipes_by_ingredients(**pic_args).json()
                   # short circuit evaluation is critical. .length() > 0 check doesn't work probably b/c this is not an array, rather a dict...
                   if sp_json and sp_json[0]:
                        picture_response_obj = requests.get(sp_json[0].get('image'), stream=True)
                        # https://stackoverflow.com/a/17011420
                        picture_binary = picture_response_obj.content
                   else:
                        # https://www.programiz.com/python-programming/methods/built-in/bytes
                        # https://requests.readthedocs.io/en/master/user/quickstart/#binary-response-content
                        # TODO HANDLE THIS ON THE FRONTEND: this is 0x30 in utf 8 (not 0x00 since it isnt supported by sql server i guess...)
                        picture_binary = bytes('0', 'utf-8')
                    
                   if cuisine:
                        self.cursor.execute(
                            'EXEC [Food_SecondaryProcessing_AddCuisineAndPicture] ?,?,?',
                            food_name,
                            cuisine,
                            picture_binary
                        )
                        # we still must do a .commit(), even with SPs...
                        self.cursor.commit()
                   else: # we can still add the "null" picture 0x30 anyway, it give the "fact" to the DB in a way that
                        # we didn't find a picture from the spoonacular api,
                        # so we won't use more unneeded api calls
                        self.cursor.execute(
                            'EXEC [Food_SecondaryProcessing_AddPictureOnly] ?,?',
                            food_name,
                            picture_binary
                        )
                        # we still must do a .commit(), even with SPs...
                        self.cursor.commit()
                else:
                    print('[i][Spoonacular API] Skipping unnecessary API call since a cuisine or picture for this particular food already exists.')
                
    
    def insert_data(self, meal_options):   
        # need to do stuff in this order b/c of Identity columns...
        self.insert_locs(meal_options)
        self.insert_meals()
        self.insert_loc_food_meal_assocs(meal_options)
        self.insert_nutrition_infos(meal_options)
        
        print('[i] PRIMARY+.5 PROCESSING - Computing meal variety scores')
        self.cursor.execute(
            'EXEC [ComputeVarietyScores]'
        )
        # we still must do a .commit(), even with SPs...
        self.cursor.commit()
        
        if not UNCONDITIONAL_SECONDARY_PROCESSING:
            if input('[!!] SECONDARY PROCESSING - INVOLVES API CALLS TO SPOONACULAR: Are you sure you want to do this? This may be costly! (Y/N): ') != 'Y':
                self.close()
                exit()
        else:
            print('[!!] SECONDARY PROCESSING - Unconditional Secondary Processing was turned on. This will use API calls.')
        self.secondary_processing_cuisines_pics(meal_options)
                
    
# Adapted from https://www.analyticsvidhya.com/blog/2017/07/web-scraping-in-python-using-scrapy/
# and https://www.linode.com/docs/development/python/use-scrapy-to-extract-data-from-html-tags/
class BonSpiderScrapySpiderSpider(scrapy.Spider):
    name = 'bon_spider_scrapy_spider_create_db'
    allowed_domains = ['rose-hulman.cafebonappetit.com']
    start_urls = ['https://rose-hulman.cafebonappetit.com/']

    def putIntoDB(self, sorted_meal_options):
        print('[i] ADDING COLLECTED INFORMATION TO DB.')

        db_conn = DatabaseConnection()
        db_conn.connect()
        
        db_conn.insert_data(sorted_meal_options)
        
        db_conn.close()

    def createDB(self):
        create_db_conn = CreateDatabaseConnection()
        create_db_conn.connect()
        
        create_db_conn.create_database()
        
        create_db_conn.close()

    def parse(self, response):
        if RUN_CREATE_DATABASE_SCRIPT:
            print('[i] Creating a new database with name %s.' % NEW_DB_NAME)
            self.createDB()
        else:
            print('[i] RUN_CREATE_DATABASE_SCRIPT is False, so the create database script will not run. The database %s will be used to add new data instead.' % NEW_DB_NAME)
    
        # 3D array: [[Meal names], [Meal locations], [Meal nutrition info], [Meal restrictions]]
        # Within meal names: [[Breakfast Meal names], [Lunch meal names], [Dinner meal names]]
        
        sorted_meal_options = self.getOptionsSortedByMeal(response)
        #print(sorted_meal_options)
        self.putIntoDB(sorted_meal_options)
		
    def getOptionsSortedByMeal(self, response):
        curr_nutr_index = 0

        # https://stackoverflow.com/questions/51946051/most-elegant-way-to-assign-multiple-variables-to-the-same-value
        names_sorted_by_meal, locations_sorted_by_meal, nutrition_sorted_by_meal, restrictions_sorted_by_meal = ([] for _ in range(4))

        # lowercase meal periods for xpath css stuff. (it doesn't work w uppercase for some reason)
        for meal_period in [period.lower() for period in MEAL_PERIODS]:
            # Get food names.

            # Useful ref: https://docs.scrapy.org/en/latest/topics/selectors.html
            # use #breakfast, #lunch, or #dinner as CSS selectors to get each individual meal. Run the script day-of
            # so you get the most up to date options then.
            food_names = response.css('#' + meal_period + ' .site-panel__daypart-item-title *::text').getall()
            #print(meal_names)
            #meal_names = [fixed_name for fixed_name in meal_names if fixed_item != '\n\t\t\t']
            #meal_names.remove(BORKED_STRING) # \/ replaces this line...
            food_names = [fixed_name.replace(BORKED_STRING, '').replace('\t', '') for fixed_name in food_names if fixed_name != '\n\t\t\t']
            names_sorted_by_meal.append(food_names)
            #print(meal_names)

            # Get their locations,
            food_locations = response.css('#' + meal_period + ' .site-panel__daypart-item-station *::text').getall()
            #print(food_locations)

            locations_sorted_by_meal.append(food_locations)

            # Get their nutrition info and restrictions (NOTE: have to get food name ... OR get value start and end index ...
            # to do further association in DB itself...),
            # edit: can't get from html :(
            # they beautifully hid it inside JS (which means selenium, not right now for me! just want sth that works!).
            # what we can do is extract the json at the top. I;m inferring thats the raw json data that
            # they use in order to generate their hidden JS monster.
            #meal_nutrition_info = response.css('#' + meal_period + ' .daypart-modal__title *::text').getall()
            #print(meal_nutrition_info)

            # e.g.:
            # <script>
			# (function() {
			# 	Bamco = (typeof Bamco !== "undefined") ? Bamco : {};
			# 	Bamco.api_url = {
			# 		items: 'https://legacy.cafebonappetit.com/api/2/items?format=jsonp',
			# 		cafes: 'https://legacy.cafebonappetit.com/api/2/cafes?format=jsonp',
			# 		menus: 'https://legacy.cafebonappetit.com/api/2/menus?format=jsonp'
			# 	};
			# 	Bamco.current_cafe = {
			# 		name: 'Café',
			# 		id: 0				};
			# 	Bamco.view_tier = 1;
			# 	Bamco.menu_items = {"5216794":{"id":"5216794","label":"scrambled eggs"...",
            #         "cor_icon":{"1":"Vegetarian","9":"Made without Gluten-Containing Ingredients"},
            #         ...,
            #         nutrition_details":{"calories":{"label":"Calories","value":"180","unit":""},
            #         "servingSize":{"label":"Serving Size","value":"4.3","unit":"oz"},...,
            #     }}
            #

            # JSON parsing time FTW!
            all_the_scripts = response.css('script').getall()
            # useful ref: https://stackoverflow.com/a/9542768
            script_to_find = next(script for script in all_the_scripts if 'Bamco.menu_items' in script)
            # and now distill it down to Bamco.menu_items entry.
            # https://stackoverflow.com/questions/15340582/python-extract-pattern-matches
            regex_pattern = re.compile('Bamco.menu_items = (.*);')
            # get matching group 1 (thing in parentheses in (.*))
            correct_json = regex_pattern.search(script_to_find).group(1)

            # I LOVE that Python natively supports JSON! Yey!
            python_json = json.loads(correct_json)
            # test: does this print the first menu item ( use [0] etc to ignore
            # the random ids that were put in there by Bon's DB)?
            #print(python_json[0])
            # https://stackoverflow.com/a/3097896
            # Go by values. Using python_json by itself just does keys by default...
            #testey_item_ = next(iter(python_json.values()))
            # THIS WORKS YAY!
            
            #print(testey_item_)
            #print(testey_item_['label'])
            # print(testey_item_['nutrition_details'])
            # print(testey_item_['nutrition_details']['fatContent']['value'])

            # one list for each info for later appending to the list by meal
            nutrition_meal_ls = []
            restrictions_meal_ls = []
            # new strategy: view all meal items but check if they're the same as in the food items list (find the entry that is the same, inefficient but
            # it works)
            # then add nutrition info / restrictions info
            for food_name in food_names:
                meal_json_item = []
                # find key by value
                for potential_json_item in list(python_json.values()):
                    if food_name.lower() == potential_json_item['label']:
                        meal_json_item = potential_json_item
                
                if meal_json_item:
                    # Get nutrition info for meal item
                    meal_json_item_nutrition_dict = meal_json_item.get('nutrition_details')
                    if meal_json_item_nutrition_dict:
                        # Being Pythonic FTW!
                        nutrition_meal_ls.append(
                            [
                                meal_json_item['label'],
                                # serving size (always in oz...)
                                float(meal_json_item_nutrition_dict['servingSize']['value']),
                                # calorie content
                                int(meal_json_item_nutrition_dict['calories']['value']),
                                # total fat content
                                float(meal_json_item_nutrition_dict['fatContent']['value']),
                                # carbs
                                int(meal_json_item_nutrition_dict['carbohydrateContent']['value']),
                                # protein
                                float(meal_json_item_nutrition_dict['proteinContent']['value'])
                            ]
                        )
                    else:
                        # appending None won't append anything, so append empty list...
                        nutrition_meal_ls.append([])
                        
                    # add restrictions (if they exist) so use .get() to do this, we don't care about the weird numbers...
                    meal_json_item_restrictions_dict = meal_json_item.get('cor_icon')
                    if meal_json_item_restrictions_dict:
                        # only get first value (if it exists), because an option can be either vegetarian or vegan (but not both)
                        # i.e. mutually excl.
                        final_restrs = [
                            r
                            for r in meal_json_item_restrictions_dict.values()
                            if r == 'Made without Gluten-Containing Ingredients' or r == 'Vegetarian' or r == 'Vegan'
                        ]
                        if final_restrs:
                            # TODO allow vegeterian + gluten free OR vegan + gluten free in DB and in here
                            # first thing to do here is just remove the [0] to get all restrs.
                            # second thing is change the way items are added to DB later on...
                            restrictions_meal_ls.append(final_restrs[0])
                        else:
                            # if meal_json_item.get('cor_icon') is None, just add 'None'...
                            restrictions_meal_ls.append('None')
                    else:
                        # appending None won't append anything, so append 'None'...
                        restrictions_meal_ls.append('None')
                # If it doesn't exist, use an empty list for nutrition and 'None' for restrictions so we input correct info in the DB.
                # (we could do it differently, e.g. have 0s for nutrition, but i want to do it this way, because of how the app will process
                # restrictions information, by showing the label. for nutrition info, it won't show a place to go to it at all)
                else:
                    nutrition_meal_ls.append([])
                    restrictions_meal_ls.append('None')
        
            nutrition_sorted_by_meal.append(nutrition_meal_ls)
            restrictions_sorted_by_meal.append(restrictions_meal_ls)

        return [names_sorted_by_meal, locations_sorted_by_meal, nutrition_sorted_by_meal, restrictions_sorted_by_meal]

    # Get all meal item options for today (as a code starting point)...
    # def getAllMealOptions(self, response):
    #     # Useful ref: https://docs.scrapy.org/en/latest/topics/selectors.html
    #     meal_text_items = response.css('.site-panel__daypart-item-title *::text').getall()
    #     #print(meal_text_items)
    #     #meal_text_items = [fixed_item for fixed_item in meal_text_items if fixed_item != '\n\t\t\t']
    #     meal_text_items.remove(BORKED_STRING)
    #     meal_text_items = [fixed_item.replace(BORKED_STRING, '').replace('\t', '') for fixed_item in meal_text_items if fixed_item != '\n\t\t\t']

    #     print(meal_text_items)
