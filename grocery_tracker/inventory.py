from __future__ import division

import os
import sys
import re
import requests
import csv
from datetime import datetime
from pprint import pprint

CONFIGS = os.path.join('.', 'config')
USER_DIR = os.path.join('D:\\', 'Dropbox')
LIST_DIR = os.path.join('apps', 'XSCANPET')

with open(os.path.join(CONFIGS, 'api_key.txt'), 'r') as f:
            t = []
            for line in f.readlines():
                t.append(tuple(line[:-1].split(' = ')))
            token = dict(t)
			
WALMART_KEY = token['WALMART_KEY']
USDA_KEY = token['USDA_KEY']

"""
UPC Database
https://upcdatabase.org/
API Key: 1bcd18940122e3f2864a600acd233bf2

USDA
Account Email: parnell.justin@gmail.com
Account ID: b61597a2-6c40-4bb1-8b66-cdbf41c25e2e
EvYdqPWGbhNJeFJvYRCdl0YMjCaAU6Sq6qMS8kHJ
"""
SAMPLE_UPC = '011110856050'
WALMART_SAMPLE_UPC = '729776413561'

USDA_UPC_SEARCH = 'https://api.nal.usda.gov/ndb/search/?format=json&q={0}&max=25&offset=0&api_key={1}'
USDA_NDB_SEARCH = 'https://api.nal.usda.gov/ndb/reports/?ndbno={0}&type=b&format=json&api_key={1}'
UIDB_UPC_SEARCH = 'https://api.upcitemdb.com/prod/trial/lookup?upc={0}'
WALMART_UPC_SEARCH = 'http://api.walmartlabs.com/v1/items?apiKey={0}&upc={1}'
# http://www.foodstoragemanagement.com/external_item.php?id=224489
# https://www.digit-eyes.com/cgi-bin/digiteyes/apiDemo.cgi
# https://devs.upcitemdb.com/
class Food:
    def __init__(self, food):
        self.name =         food['name']
        self.source =       food['source']
        self.serving =      food['serving']
        self.nutrients =    food['nutrients']
        self.full_mass =    1.0 if food['full_mass'] is None else food['full_mass']

        self.upc =          food['upc']
        self.percent_full = food['percent_full']
        self.current_mass = self.percent_full * self.full_mass
        self.expiration =   food['expiration']

    def set_mass(self, new_percent=None, new_mass=None):
        if new_percent is not None and new_mass is not None:
            print "Please specify either a new percent or a new mass, not both"
        elif new_percent:
            self.percent_full = new_percent
            self.current_mass = self.full_mass * self.percent_full
        elif new_mass:
            self.current_mass = new_mass
            self.percent_full = new_mass / self.full_mass
        else:
            print "Please specify either a new percent or a new mass"
        return

def usda_food_lookup(upc):
    upc_matches = requests.get(USDA_UPC_SEARCH.format(upc, USDA_KEY)).json()
    if u'errors' in upc_matches.keys():
        raise RuntimeError("Search did not return any results")

    ndb = upc_matches[u'list'][u'item'][0][u'ndbno']

    food = requests.get(USDA_NDB_SEARCH.format(ndb, USDA_KEY)).json()
    food = food[u'report'][u'food']

    pprint(food[u'name'])
    parsed_food = dict(name=        food[u'name'],
                   source=      {'source': 'USDA NDB', 'id': food[u'ndbno']},
                   serving=     {'name': food[u'nutrients'][0][u'measures'][0][u'label'],
                                 'unit': food[u'nutrients'][0][u'measures'][0][u'eunit'],
                                 'value': food[u'nutrients'][0][u'measures'][0][u'value']},
                   nutrients=   [{'name': n[u'name'],
                                  'unit': n[u'unit'],
                                  'value': eval(n[u'value'])} for n in food[u'nutrients']],
                   full_mass=   None
                   )
    return parsed_food

def upcitemdb_lookup(upc):
    upc_matches = requests.get(UIDB_UPC_SEARCH.format(upc)).json()
    if upc_matches[u'code'] != 'OK':
        raise RuntimeError("Search did not return any results")

    food = upc_matches[u'items'][0]

    parsed_food = dict(name=        food[u'title'],
                       source=      {'source': 'UPC Item DB', 'id': None},
                       serving=     None,
                       nutrients=   None,
                       full_mass=   food[u'weight']
                       )

    return parsed_food

def walmart_lookup(upc):
    upc_matches = requests.get(WALMART_UPC_SEARCH.format(WALMART_KEY, upc)).json()
    if u'errors' in upc_matches.keys():
        raise RuntimeError('UPC not found')

    item_id = upc_matches[u'items'][0][u'itemId']
    item = requests.get('https://www.walmart.com/product/mobile/api/{0}'.format(item_id)).json()
    if u'status' in item.keys():
        raise RuntimeError('Walmart item not found')

    print(item[u'idml'][u'idmlMap'][u'Modules'][u'ShortDescription'][0][u'displayValue'])

    try:
        nutrition_facts_base = item[u'idml'][u'idmlMap'][u'Modules'][u'NutritionFacts']
    except KeyError:
        print "No nutrition facts for this item"
        return None

    try:
        key_nutrients = nutrition_facts_base[u'key_nutrients'][u'children']
    except KeyError:
        key_nutrients = []
        print "No key nutrients, continuing"

    try:
        calorie_information = nutrition_facts_base[u'calorie_information'][u'children']
    except KeyError:
        calorie_information = []
        print "No calorie information, continuing"

    nutrition_facts = key_nutrients + calorie_information
    nutrition_fact_data = {}
    for parent in nutrition_facts:
        if u'children' in parent[u'valueMap']:
            for child in parent[u'valueMap'][u'children']:
                nutrition_fact_data[child[u'nutrient_name'][u'displayValue']] = child[u'nutrient_amount'][u'values'][0]
            continue
        try:    nutrition_fact_data[parent[u'valueMap'][u'nutrient_name'][u'displayValue']] = parent[u'valueMap'][u'nutrient_amount'][u'values'][0]
        except: nutrition_fact_data[parent[u'valueMap'][u'nutrient_name'][u'displayValue']] = '0 G'


    try:
        serving_size = item[u'idml'][u'idmlMap'][u'Modules'][u'NutritionFacts'][u'serving_information'][u'children']
        print serving_size
        serving_size_data = {'serving_size': serving_size[0][u'valueMap'][u'serving_size'][u'values'][0],
                             'per_container': serving_size[1][u'valueMap'][u'servings_per_container'][u'values'][0]}
    except:
        print "No serving size information, applying defaults"
        serving_size_data = {'serving_size': '0 G',
                             'per_container': '1'}

    serving = {}

    n = re.match('([^0-9]+)', serving_size_data['serving_size'])

    if n is not  None:   serving['name'] = n.group(0)
    else:               serving['name'] = None

    u = re.match('([^0-9]+)', serving_size_data['serving_size'])

    if u is not None:   serving['unit'] = u.group(0)
    else:               serving['unit'] = None

    v = re.match('([0-9]+)', serving_size_data['serving_size'])

    if v is not None:   serving['value'] = v.group(0)
    else:               serving['value'] = None

    print serving

    parsed_food = dict(name=item[u'idml'][u'idmlMap'][u'Modules'][u'ShortDescription'][0][u'displayValue'],
                       source={'source': 'Walmart DB', 'id': item_id},
                       serving=serving,
                       nutrients=[{'name':name,
                                   'unit': ' '.join(quantity.split(' ')[1:]),
                                   'value': quantity.split(' ')[0]} for name, quantity in nutrition_fact_data.iteritems()]
                       )
    spc = serving_size_data['per_container']
    spc = re.match('([0-9]+)', spc)

    if spc is not None:     spc = spc.group(0)
    else:                   spc = "1"

    parsed_food['full_mass'] = {'unit': parsed_food['serving']['unit'],
                                'value': eval(parsed_food['serving']['value']) * eval(spc)}
    return parsed_food



def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]

if __name__ == '__main__':

    with open(os.path.join(USER_DIR, LIST_DIR, 'initial_inventory_test.csv'), 'r') as infile:

        reader = unicode_csv_reader(infile)
        result = {}
        headers = reader.next()
        headers[0] = u'upc'
        queue = []
        for row in reader:
            queue.append(dict(zip(headers, row)))

    matches = []
    # USDA Lookup
    # if queue:
    #     for _ in xrange(0, len(queue)):
    #         item = queue.pop(0)
    #         try:
    #             food_data = usda_food_lookup(upc=item['upc'])
    #             matches.append(food_data)
    #         except RuntimeError:
    #             queue.append(item)

    # Walmart Lookup
    if queue:
        for _ in xrange(0, len(queue)):
            item = queue.pop(0)
            try:
                food_data = walmart_lookup(upc=item['upc'])
                matches.append(food_data)
            except RuntimeError:
                queue.append(item)
