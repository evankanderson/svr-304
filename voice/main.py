import json
import random
import logging

from model import model
from google.auth.transport import requests
from google.cloud import firestore
from google.oauth2 import id_token

db = firestore.Client()
settings = {}


def extract_user(request_json):
  request_json = request_json.get('originalDetectIntentRequest', {}).get('payload', {})
  logging.info(f'User is: "{request_json.get("user")}"')
  jwt = request_json.get('user', {}).get('idToken', '')
  if not jwt:
    return {'name': 'Anonymous', 'sub': 0}
  auth_request = requests.Request()
  info = id_token.verify_oauth2_token(jwt, auth_request)
  if info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
    raise AssertionError('Wrong JWT issuer: %s', info['iss'])
  return info


def sale_items(request_json):
    quote = request_json['queryResult'].get('fulfillmentText', 'Nothing')
    return dict(fulfillmentText='I said "%s"' % quote)


def welcome(request_json):
    OPTS = [
        ' How may I serve you today?', ' It\'s a great day for a demo.',
        ' What can I get for you?'
    ]
    return dict(fulfillmentText=random.choice(OPTS))


def list_menu(request_json):
    dishes = [x for x in model.AllDishes(db)]
    concat = ', '.join((x.name for x in dishes))
    count = len(dishes)
    user = extract_user(request_json)
    logging.info(f'User is {user}')
    OPTS = [
      f'We have {count} items on the menu: {concat}',
      f'{user["given_name"]}, I have {concat}'
    ]
    return dict(fulfillmentText=random.choice(OPTS))


def start_order(request_json):
    # create a context for items to be added
    return dict(fulfillmentText='Not implemented yet.')


def add_item(request_json):
    user = extract_user(request_json)
    if not 'email' in 'user':
      return dict(fulfillmentText='Please log in first')
    return dict(fulfillmentText=f'Got it, {user["email"]}')

HANDLERS = {
    'sale items': sale_items,
    'Default Welcome Intent': welcome,
    'ls': list_menu,
    'buy': start_order,
    'add': add_item,
}


def build_response(request_json):
    """Builds a dialogflow response to the given query.

    Arguments:
      request_json {dict} -- The dictionary request object

    Returns:
      {dict} Dialogflow response
    """
    intent = request_json['queryResult']['intent']['displayName']
    handler = HANDLERS[intent]
    print("Intent is %s" % intent)
    return handler(request_json)


def voice(request):
    data = request.get_json()
    logging.info("Got message: %s",
                    json.dumps(data, sort_keys=True))
    response = build_response(data)
    return json.dumps(response)


if __name__ == "__main__":
    import flask
    app = flask.Flask(__name__)

    @app.route("/", methods=["POST"])
    def default():
        return voice(flask.request)

    app.run("127.0.0.1", 8000, debug=True)
    logging = app.logger
