# -*- coding: utf-8 -*-
import datetime
import json
import re # regex ftw!
import pyodbc # for ODBC
import random # for random picking
import scrapy
import spoonacular # for spoonacular api.

# https://stackoverflow.com/a/316253
#from decimal import Decimal


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
    # no longer Password123. It is now a different one, thanks to DB maintainer.
    ODBC_STRING = 'DRIVER={ODBC Driver 17 for SQL Server};\
        SERVER=server.com;DATABASE=BonFoodTracker19;\
        UID=dbappuser;PWD=dbapppassword'
    SPOONACULAR_API_KEY = 'spoonacular_api_key_here'
    
    def __init__(self):
        self.sp_api = spoonacular.API(self.SPOONACULAR_API_KEY)
    
    def connect(self):
        self.conn = pyodbc.connect(self.ODBC_STRING)
        self.cursor = self.conn.cursor()
        # maybe that will fix stuff?
        self.cursor.execute('USE BonFoodTracker19;')

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
                # dupe the ingredient/food option b/c we don't care...
                cuisine = self.sp_api.classify_cuisine(food_name, food_name).json()['cuisine']
                
                pic_args = {'ingredients': food_name, 'limitLicense': True, 'number': '1', 'ranking': '1'}
                # https://stackoverflow.com/questions/30229231/python-save-image-from-url/30229298
                import requests
                # for testing/debugging...
                #result = self.sp_api.search_recipes_by_ingredients(**pic_args).json()
                #import ipdb; ipdb.set_trace()
                # get an image if possible... else don't worry about importing it...
                sp_json = self.sp_api.search_recipes_by_ingredients(**pic_args).json()
                if sp_json and len(sp_json) > 0:
                    picture_response_obj = requests.get(sp_json[0]['image'], stream=True)
                    # https://stackoverflow.com/a/17011420
                    picture_binary = picture_response_obj.content
                else:
                    # https://www.programiz.com/python-programming/methods/built-in/bytes
                    # https://requests.readthedocs.io/en/master/user/quickstart/#binary-response-content
                    # TODO HANDLE THIS ON THE FRONTEND: this is 0x30 in utf 8 (not 0x00 since it isnt supported by sql server i guess...)
                    picture_binary = bytes('0', 'utf-8')
                
                self.cursor.execute(
                    'EXEC [Food_SecondaryProcessing_AddCuisineAndPicture] ?,?,?',
                    food_name,
                    cuisine,
                    picture_binary
                )
                # we still must do a .commit(), even with SPs...
                self.cursor.commit()
                
    
    def insert_data(self, meal_options):   
        # need to do stuff in this order b/c of Identity columns...
        self.insert_locs(meal_options)
        self.insert_meals()
        self.insert_loc_food_meal_assocs(meal_options)
        self.insert_nutrition_infos(meal_options)
        if input("SECONDARY PROCESSING - INVOLVES API CALLS TO SPOONACULAR: Are you sure you want to do this? This may be costly! (Y/N)") != "Y":
            exit()
        self.secondary_processing_cuisines_pics(meal_options)
                
    
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

            # Thanks internship!
            #import ipdb; ipdb.set_trace()


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