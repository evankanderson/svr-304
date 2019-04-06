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


def fetch_entities(database):
    for dish in database.collection('dishes').list_documents():
        for ingredient in dish.collection('ingredients').stream():
            yield ingredient


def write_entity(name, options_list, entity):
    name = name.capitalize()
    entity_path = os.path.join('dialogflow', 'entities', name + '.json')
    en_path = os.path.join('dialogflow', 'entities', name + '_entries_en.json')
    base_entity = {
        'isOverridable': True,
        'isEnum': False,
        'automatedExpansion': True
    }
    with open(entity_path, 'w') as entity_file, open(en_path, 'w') as en_file:
        if 'uuid' not in entity.to_dict():
            entity.reference.update({'uuid': str(uuid.uuid1())})
            entity = entity.reference.get()
            print('Added uuid to %s: %s' % (entity.reference.path,
                                            entity.get('uuid')))
        entity_metadata = {'uuid': entity.get('uuid'), 'name': name}
        entity_metadata.update(base_entity)
        json.dump(entity_metadata, entity_file, indent=2)
        en_entities = []
        for o in options_list:
            en_entities.append({'value': o, 'synonyms': [o]})
        json.dump(en_entities, en_file, indent=2)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout)
    entities = fetch_entities(db)

    i = 0
    for entity in entities:
        i += 1
        print('Entity at %s is %s' % (entity.reference.path, entity.to_dict()))
        write_entity(entity.reference.id, entity.get('names'), entity)

    print('Found %d entities!' % i)
