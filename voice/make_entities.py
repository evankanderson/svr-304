"""Auto-generate Dialogflow entities from Firestore resources.

Usage:
  python make_entities.py

Note: you must have already configured your Google Cloud credentials.
This only generates the JSON files which need to be imported into Dialogflow.
To import, zip the entire "dialogflow" folder and upload using the "import
from zip" option in the Dialogflow console.
"""

import json
import logging
import os
import sys
import uuid
from google.cloud import firestore

db = firestore.Client()

BASE_ENTITY = {
    'isOverridable': True,
    'isEnum': False,
    'automatedExpansion': True
}

DISH_UUID = '4f9af8e1-9c3d-42bc-8c59-41afde4a15b5'
INGREDIENTS_UUID = '412b8e29-ae93-4073-b8a1-c70d6eae5113'


def fetch_dishes(database):
    for dish in database.collection('dishes').stream():
        yield dish


def fetch_entities(database):
    for dish in database.collection('dishes').list_documents():
        for ingredient in dish.collection('ingredients').stream():
            yield ingredient


def write_items(uuid, name, item_list):
    name = name.capitalize()
    entity_path = os.path.join('dialogflow', 'entities', name + '.json')
    en_path = os.path.join('dialogflow', 'entities', name + '_entries_en.json')
    with open(entity_path, 'w') as entity_file, open(en_path, 'w') as en_file:
        entity_data = {'uuid': uuid, 'name': name}
        entity_data.update(BASE_ENTITY)
        json.dump(entity_data, entity_file, indent=2)
        en_entities = []
        for item in item_list:
            en_entities.append({'value': item})
        json.dump(en_entities, en_file, indent=2)


def write_entity(name, options_list, entity):
    name = name.capitalize()
    entity_path = os.path.join('dialogflow', 'entities', name + '.json')
    en_path = os.path.join('dialogflow', 'entities', name + '_entries_en.json')

    with open(entity_path, 'w') as entity_file, open(en_path, 'w') as en_file:
        if 'uuid' not in entity.to_dict():
            entity.reference.update({'uuid': str(uuid.uuid1())})
            entity = entity.reference.get()
            print('Added uuid to %s: %s' % (entity.reference.path,
                                            entity.get('uuid')))
        entity_metadata = {'uuid': entity.get('uuid'), 'name': name}
        entity_metadata.update(BASE_ENTITY)
        json.dump(entity_metadata, entity_file, indent=2)
        en_entities = []
        for o in options_list:
            en_entities.append({'value': o, 'synonyms': [o]})
        json.dump(en_entities, en_file, indent=2)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout)

    dishes = fetch_dishes(db)
    write_items(DISH_UUID, 'Dishes', (x.reference.id for x in dishes))

    entities = fetch_entities(db)

    all_ingredients = []

    i = 0
    for entity in entities:
        i += 1
        print('Entity at %s is %s' % (entity.reference.path, entity.to_dict()))
        write_entity(entity.reference.id, entity.get('names'), entity)
        all_ingredients.extend((x for x in entity.get('names')))

    write_items(INGREDIENTS_UUID, 'Ingredients', all_ingredients)

    print('Found %d entities!' % i)
