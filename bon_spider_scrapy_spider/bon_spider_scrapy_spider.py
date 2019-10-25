# -*- coding: utf-8 -*-
import datetime
import json
import re # regex ftw!
import pyodbc # for ODBC
import random # for random picking
import scrapy


BORKED_STRING = '\n\t\t\t'

TODAY_WEEKDAY = datetime.date.today().weekday()
TODAY_STRFTIME = datetime.datetime.now().strftime('%Y-%m-%d')
# hacky workaround for saturday and sunday brunch/dinner.
MEAL_PERIODS = []
if TODAY_WEEKDAY == 5:
    MEAL_PERIODS = ['Brunch']
elif TODAY_WEEKDAY == 6:
    MEAL_PERIODS = ['Brunch', 'Dinner']
else:
    MEAL_PERIODS = ['Breakfast', 'Lunch', 'Dinner']

# for testing only, if you do in a cmd prmpt window/terminal:
# python bon_spider_scrapy_spider.py
# rather than run it with: scrapy crawl bon_spider_scrapy_spider
# https://stackoverflow.com/questions/419163/what-does-if-name-main-do
if __name__ == 'main':
    print('[i][DEBUG] TESTING DB CONNECTION ONLY. NOT INSERTING ANYTHING.')
    # Test DB connection.
    db_conn = DatabaseConnection()
    db_conn.connect()
    #db_conn.insert_data()
    db_conn.close()

class DatabaseConnection():
    ODBC_STRING = 'DRIVER={ODBC Driver 17 for SQL Server};\
        SERVER=server.com;DATABASE=BonFoodTracker19;\
        UID=dbappuser;PWD=dbapppassword'
    
    def __init__(self):
        pass
    
    def connect(self):
        self.conn = pyodbc.connect(self.ODBC_STRING)
        self.cursor = self.conn.cursor()

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
                    # DON'T FORGET TO COMMIT WITH PYODBC! https://stackoverflow.com/a/20199702
                    # also used https://stackoverflow.com/a/9521382                
                    self.cursor.execute(
                        'INSERT INTO BonLocation(LocationName, Traffic) VALUES(?, ?);',
                        loc,
                        random_traffic
                    )
                    self.cursor.commit()
                
            meal_period_index = 0
            type_index = type_index + 1

    def insert_nutrition_infos(self, meal_options):
        pass


    def insert_loc_food_meal_assocs(self, meal_options):
        food_index = 0
        meal_index = 0
        foods = meal_options[0]

        for meal_locs in meal_options[1]:
            # add meal locations for a particular period,
            # associated with a particular food...
            
            # for Frequency as a computed column, get the count of the item
            # once we put it in the table.            
            for food_meal_loc in meal_locs:
                # TODO do we need TRY/EXCEPT if food already exists?
                
                # get its frequency first
                self.cursor.execute(
                    'SELECT COUNT(FoodName)\
                        FROM Food\
                        WHERE FoodName = ? \
                        GROUP BY FoodName',
                    foods[meal_index][food_index]
                )
                
                # +1 b/c how i intended it to originally work for potentially updating frequency in the db later...
                food_freq_arr_tuple_thingy = self.cursor.fetchall()
                food_freq = food_freq_arr_tuple_thingy[0][0] + 1 if food_freq_arr_tuple_thingy else 1
                
                # add the food itself
                if food_freq > 1:
                    self.cursor.execute(
                        'UPDATE Food\
                        SET Frequency = ?\
                        WHERE FoodName = ?',
                        food_freq,
                        foods[meal_index][food_index]
                    )
                    self.cursor.commit()
                else:
                    food_restrictions = meal_options[3][meal_index][food_index]
                    #print(len(meal_options[3][meal_index][food_index]))
                    # TODO modify food_addfood SP so we can easily do this?
                    self.cursor.execute(
                        'INSERT INTO Food(FoodName, Frequency, Restrictions)\
                        VALUES (?,?,?)',
                        foods[meal_index][food_index],
                        food_freq,
                        food_restrictions
                    )
                    self.cursor.commit()
                    
                # current food is now mapped to this particular meal date/period
                self.cursor.execute(
                    'SELECT Food_ID\
                    FROM Food\
                    WHERE FoodName = ?',
                    foods[meal_index][food_index]
                )
                # for queries (not changing the db statements), use cursor.fetchall(), not cursor.commit()...
                # https://stackoverflow.com/a/11451863
                food_id = self.cursor.fetchall()[0][0]
                     
                self.cursor.execute(
                    # it's called FoodID in serves, not Food_ID...
                    # TODO _maybe_ fix this unless this causes too many issues later?
                    'INSERT INTO Serves(MealDate, MealPeriod, FoodID)\
                    VALUES (?,?,?)',
                    TODAY_STRFTIME,
                    MEAL_PERIODS[meal_index],
                    food_id
                )
                self.cursor.commit()
                    
                # add it to the mapped food -> location things
                # TODO make an "add (food by name) to (location by name)" SP?
                self.cursor.execute(
                    'SELECT Location_ID\
                    FROM BonLocation\
                    WHERE LocationName = ?',
                    food_meal_loc
                )
                # get just the first location id, don't care about other things in the returned tuple...
                food_loc_id = self.cursor.fetchall()[0][0]
                
                self.cursor.execute(
                    'IF NOT EXISTS(SELECT Food_ID FROM ServedAt WHERE Food_ID = ? AND Location_ID = ?) BEGIN\
                        INSERT INTO ServedAt(Food_ID, Location_ID)\
                        VALUES (?,?)\
                    END',
                    food_id,
                    food_loc_id,
                    food_id,
                    food_loc_id
                )
                self.cursor.commit()
                
                food_index += 1
                
    
            food_index = 0
            meal_index = meal_index + 1
    
    def insert_meals(self):
        for meal_period in MEAL_PERIODS:
            self.cursor.execute(
                'IF NOT EXISTS (SELECT MealDate FROM Meal WHERE MealDate = ? AND MealPeriod = ?) BEGIN\
                    INSERT INTO Meal(MealDate, MealPeriod)\
                    VALUES(?,?)\
                END',
                TODAY_STRFTIME,
                meal_period,
                TODAY_STRFTIME,
                meal_period
            )
            self.cursor.commit()
    
    def insert_data(self, meal_options):   
        # need to do stuff in this order b/c of Identity columns...
        self.insert_locs(meal_options)
        self.insert_meals()
        self.insert_loc_food_meal_assocs(meal_options)
        self.insert_nutrition_infos(meal_options)
    
# Adapted from https://www.analyticsvidhya.com/blog/2017/07/web-scraping-in-python-using-scrapy/
# and https://www.linode.com/docs/development/python/use-scrapy-to-extract-data-from-html-tags/
class BonSpiderScrapySpiderSpider(scrapy.Spider):
    name = 'bon_spider_scrapy_spider'
    allowed_domains = ['rose-hulman.cafebonappetit.com']
    start_urls = ['https://rose-hulman.cafebonappetit.com/']

    def putIntoDB(self, sorted_meal_options):
        print('[i] ADDING COLLECTED INFORMATION TO DB.')

        db_conn = DatabaseConnection()
        db_conn.connect()
        
        db_conn.insert_data(sorted_meal_options)
        
        db_conn.close()

    def parse(self, response):
        # 3D array: [[Meal names], [Meal locations], [Meal nutrition info], [Meal restrictions]]
        # Within meal names: [[Breakfast Meal names], [Lunch meal names], [Dinner meal names]]
        sorted_meal_options = self.getOptionsSortedByMeal(response)
        print(sorted_meal_options)
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
            meal_names = response.css('#' + meal_period + ' .site-panel__daypart-item-title *::text').getall()
            #print(meal_names)
            #meal_names = [fixed_name for fixed_name in meal_names if fixed_item != '\n\t\t\t']
            #meal_names.remove(BORKED_STRING) # \/ replaces this line...
            meal_names = [fixed_name.replace(BORKED_STRING, '').replace('\t', '') for fixed_name in meal_names if fixed_name != '\n\t\t\t']
            names_sorted_by_meal.append(meal_names)
            #print(meal_names)

            # Get their locations,
            meal_locations = response.css('#' + meal_period + ' .site-panel__daypart-item-station *::text').getall()
            #print(meal_locations)

            locations_sorted_by_meal.append(meal_locations)

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

            # Thanks internship!
            #import ipdb; ipdb.set_trace()


            # one list for each info for later appending to the list by meal
            nutrition_meal_ls = []
            restrictions_meal_ls = []
            # restrict this to [curr_nutr_index : curr_nutr_index + number of breakfast items]
            for meal_json_item in list(python_json.values())[curr_nutr_index : curr_nutr_index+len(meal_locations)]:
                # If it doesn't exist, have a ~None ("null") object~ empty list
                # as temporary for database import (it will skip over it).
                meal_json_item_nutrition_dict = meal_json_item.get('nutrition_details')

                if meal_json_item_nutrition_dict:
                    # Being Pythonic FTW!
                    nutrition_meal_ls.append(
                        [
                            meal_json_item['label'],
                            # serving size (always in oz...)
                            meal_json_item_nutrition_dict['servingSize']['value'],
                            # calorie content
                            meal_json_item_nutrition_dict['calories']['value'],
                            # total fat content
                            meal_json_item_nutrition_dict['fatContent']['value'],
                            # carbs
                            meal_json_item_nutrition_dict['carbohydrateContent']['value'],
                            # protein
                            meal_json_item_nutrition_dict['proteinContent']['value']
                        ]
                    )
                else:
                    # appending None won't append anything :(, so append empty list...
                    nutrition_meal_ls.append([])
                
                # add restrictions (if they exist), we don't care about the weird numbers...
                # if meal_json_item.get('cor_icon') is None, just add None...
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
                        restrictions_meal_ls.append('None')
                else:
                    # appending None won't append anything :(, so append 'None'...
                    restrictions_meal_ls.append('None')

            # increment it for the next meal...
            curr_nutr_index = curr_nutr_index + len(meal_locations)
            print(restrictions_meal_ls)
        
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