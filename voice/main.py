"""Main dialogflow webhook handler, handles interactive voice prompts.

See the `voice` function and the HANDLERS map for the dispatch of specific
Intents.

To deploy:
  gcloud functions deploy voice --runtime python37 --trigger-http
"""

import json
import random
import logging

from model import model
from google.auth.transport import requests
from google.cloud import firestore
from google.oauth2 import id_token

db = firestore.Client()
settings = {}


def ensure_settings():
    if not settings:
        config = db.document('config/app').get()
        settings.update(config.to_dict())


def response(text: str, **kwargs):
    resp = {'fulfillmentText': text}
    resp.update(kwargs)
    logging.info(f'Responding with: "{resp}"')
    return resp


def extract_user(request_json: dict):
    request_json = request_json.get('originalDetectIntentRequest', {}).get(
        'payload', {})
    logging.info(f'User is: "{request_json.get("user")}"')
    jwt = request_json.get('user', {}).get('idToken', '')
    if not jwt:
        return {'name': 'Anonymous', 'sub': 0}
    auth_request = requests.Request()
    info = id_token.verify_oauth2_token(jwt, auth_request)
    if info['iss'] not in [
            'accounts.google.com', 'https://accounts.google.com'
    ]:
        raise AssertionError('Wrong JWT issuer: %s', info['iss'])
    return info


def sale_items(request_json: dict):
    quote = request_json['queryResult'].get('fulfillmentText', 'Nothing')
    return response('I said "%s"' % quote)


def welcome(request_json: dict):
    OPTS = [
        ' How may I serve you today?', ' It\'s a great day for a demo.',
        ' What can I get for you?'
    ]
    return response(random.choice(OPTS))


def list_menu(request_json: dict):
    dishes = [x for x in model.AllDishes(db)]
    concat = ', '.join(('a ' + x.name for x in dishes))
    count = len(dishes)
    user = extract_user(request_json)
    logging.info(f'User is {user}')
    OPTS = [
        f'We have {count} items on the menu: {concat}', f'We have {concat}'
    ]
    return response(random.choice(OPTS))


def start_order(request_json: dict):
    ensure_settings()
    # Request transaction to be set up.
    return {
        'payload': {
            'google': {
                'expectUserResponse': True,
                'systemIntent': {
                    'intent': 'actions.intent.TRANSACTION_REQUIREMENTS_CHECK',
                    'data': {
                        '@type':
                        'type.googleapis.com/google.actions.v2.TransactionRequirementsCheckSpec',
                        'orderOptions': {
                            'requestDeliveryAddress': False
                        },
                        'paymentOptions': {
                            'googleProvidedOptions': {
                                'supportedCardNetworks':
                                ['VISA', 'MASTERCARD'],
                                'tokenizationParameters': {
                                    'tokenizationType': 'PAYMENT_GATEWAY',
                                    'parameters': {
                                        'gateway':
                                        'square',
                                        'gatewayMerchantId':
                                        settings.get('square_id', 'TODO'),
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    # followup = {
    #     'name': 'actions.intent.TRANSACTION_REQUIREMENTS_CHECK',
    #     'languageCode': 'en',
    #     'parameters': {
    #         'orderOptions': { 'requestDeliveryAddress': False},
    #         'paymentOptions': {
    #             'googleProvidedOptions': {
    #                 'supportedCardNetworks': ['VISA', 'MASTERCARD'],
    #                 'tokenizationParameters': {
    #                     'tokenizationType': 'PAYMENT_GATEWAY',
    #                     'parameters': {
    #                         'gateway': 'square',
    #                         'gatewayMerchantId': settings.get(
    #                             'square_id', 'TODO'),
    #                     }
    #                 }
    #             }
    #         }
    #     }
    # }

    # r = response(
    #     'Not implemented yet.',
    #     #followupEventInput=followup,
    #     outputContexts=request_json.get('queryResult', {}).get(
    #         'outputContexts', []))
    # logging.info(f'Returning "{r}""')
    # return r


def validate_payment(request_json: dict):
    inputs = request_json.get('originalDetectIntentRequest', {}).get(
        'payload', {}).get('inputs', [])
    okay = False
    logging.info(f'Looking in inputs: {inputs}')
    for item in inputs:
        args = item.get('arguments', [])
        for arg in args:
            if arg.get('name') == 'TRANSACTION_REQUIREMENTS_CHECK_RESULT':
                okay = arg.get('extension', {}).get('resultType') == 'OK'
    if not okay:
        return response('Sorry, I couldn\'t get transaction information.')

    user = extract_user(request_json)
    _, doc = db.collection('orders').add({'user': user['sub'], 'items': []})

    logging.info(doc.__dict__)

    order_context = {
        'name': f'{request_json["session"]}/contexts/order',
        'lifespanCount': 5,
        'parameters': {
            'orderId': doc.id,
        }
    }
    return response(
        'Okay, let\'s start your order',
        outputContexts=[order_context],
        followupEventInput={
            'name': 'menu',
            'languageCode': 'en'
        })


def add_item(request_json: dict):
    user = extract_user(request_json)
    if 'email' not in 'user':
        return response('Please log in first')
    return response(f'Got it, {user["email"]}')


def test(request_json: dict):
    return response('Dynamic answer')


HANDLERS = {
    'sale items': sale_items,
    'Default Welcome Intent': welcome,
    'ls': list_menu,
    'buy': start_order,
    'start': validate_payment,
    'add': add_item,
    'test': test,
}


def build_response(request_json: dict):
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
    logging.info("Got message: %s", json.dumps(data, sort_keys=True))
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
