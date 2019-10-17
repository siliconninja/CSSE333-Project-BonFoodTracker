# -*- coding: utf-8 -*-
import json
import re # regex ftw!
import scrapy

BORKED_STRING = '\n\t\t\t'

# Adapted from https://www.analyticsvidhya.com/blog/2017/07/web-scraping-in-python-using-scrapy/
# and https://www.linode.com/docs/development/python/use-scrapy-to-extract-data-from-html-tags/
class BonSpiderScrapySpiderSpider(scrapy.Spider):
    name = 'bon_spider_scrapy_spider'
    allowed_domains = ['rose-hulman.cafebonappetit.com']
    start_urls = ['https://rose-hulman.cafebonappetit.com/']

    def parse(self, response):
        # 2D array: [[Breakfast options], [Lunch options], [Dinner options]]
        sorted_meal_options = self.getOptionsSortedByMeal(response)
        print(sorted_meal_options)

    def getOptionsSortedByMeal(self, response):
        curr_nutr_index = 0

        # https://stackoverflow.com/questions/51946051/most-elegant-way-to-assign-multiple-variables-to-the-same-value
        names_sorted_by_meal, locations_sorted_by_meal, nutrition_sorted_by_meal, restrictions_sorted_by_meal = ([] for _ in range(4))

        for meal_period in ['breakfast', 'lunch', 'dinner']:
            # Get food names.

            # Useful ref: https://docs.scrapy.org/en/latest/topics/selectors.html
            # use #breakfast, #lunch, or #dinner as CSS selectors to get each individual meal. Run the script day-of
            # so you get the most up to date options then.
            meal_names = response.css('#' + meal_period + ' .site-panel__daypart-item-title *::text').getall()
            #print(meal_names)
            #meal_names = [fixed_name for fixed_name in meal_names if fixed_item != '\n\t\t\t']
            meal_names.remove(BORKED_STRING)
            meal_names = [fixed_name.replace(BORKED_STRING, '').replace('\t', '') for fixed_name in meal_names if fixed_name != '\n\t\t\t']
            names_sorted_by_meal.append(meal_names)

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


            # restrict this to [curr_nutr_index : curr_nutr_index + number of breakfast items]
            for meal_json_item in list(python_json.values())[curr_nutr_index : curr_nutr_index+len(meal_locations)]:
                # If it doesn't exist, have a ~None ("null") object~ empty list
                # as temporary for database import (it will skip over it).
                meal_json_item_nutrition_dict = meal_json_item.get('nutrition_details')

                if meal_json_item_nutrition_dict:
                    # Being Pythonic FTW!
                    nutrition_sorted_by_meal.append(
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
                    nutrition_sorted_by_meal.append([])
                
                # add restrictions (if they exist), we don't care about the weird numbers...
                # if meal_json_item.get('cor_icon') is None, just add None...
                meal_json_item_restrictions_dict = meal_json_item.get('cor_icon')
                if meal_json_item_restrictions_dict:
                    # only get first value (if it exists), because an option can be either vegetarian or vegan (but not both)
                    # i.e. mutually excl.
                    final_restrs = [r for r in meal_json_item_restrictions_dict.values() if r == 'Vegetarian' or r == 'Vegan']
                    if final_restrs:
                        restrictions_sorted_by_meal.append(final_restrs[0])
                    else:
                        restrictions_sorted_by_meal.append([])
                else:
                    # appending None won't append anything :(, so append empty list...
                    restrictions_sorted_by_meal.append([])

            # increment it for the next meal...
            curr_nutr_index = curr_nutr_index + len(meal_locations)

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