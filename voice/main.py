"""Main dialogflow webhook handler, handles interactive voice prompts.

See the `voice` function and the HANDLERS map for the dispatch of specific
Intents.

To deploy:
  gcloud functions deploy voice --runtime python37 --trigger-http
"""

import json
import math
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


def get_context(response_json, suffix):
    contexts = response_json.get('queryResult', {}).get('outputContexts', [])
    for c in contexts:
        if c.get('name', '').endswith(suffix):
            return c.get('parameters', {})
    return {}


def payment_data(settings, subtype):
    return {
        '@type': f'type.googleapis.com/google.actions.v2.{subtype}',
        'orderOptions': {
            'requestDeliveryAddress': False
        },
        'paymentOptions': {
            'googleProvidedOptions': {
                'supportedCardNetworks': ['VISA', 'MASTERCARD'],
                'tokenizationParameters': {
                    'tokenizationType': 'PAYMENT_GATEWAY',
                    'parameters': {
                        'gateway': 'square',
                        'gatewayMerchantId': settings.get('square_id', 'TODO'),
                    }
                }
            }
        }
    }


def to_price(value: float):
    frac, units = math.modf(value)
    return {
        'type': 'ACTUAL',
        'amount': {
            'currencyCode': 'USD',
            'units': units,
            'nanos': frac * 1000000000,
        }
    }


def read_argument(request_json: dict, argument_name: str):
    inputs = request_json.get('originalDetectIntentRequest', {}).get(
        'payload', {}).get('inputs', [])
    logging.info(f'Looking in inputs: {inputs}')
    for item in inputs:
        args = item.get('arguments', [])
        for arg in args:
            if arg.get('name') == argument_name:
                return arg.get('extension', {})
    logging.info(f'Couldn\'t find {argument_name} in {inputs}')
    return {}


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
    human = ['a ' + x.name for x in dishes]
    human[-1] = 'and ' + human[-1]
    concat = ', '.join(human)
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
                    'intent':
                    'actions.intent.TRANSACTION_REQUIREMENTS_CHECK',
                    'data':
                    payment_data(settings, 'TransactionRequirementsCheckSpec')
                }
            }
        }
    }


def validate_payment(request_json: dict):
    checkResult = read_argument(request_json,
                                'TRANSACTION_REQUIREMENTS_CHECK_RESULT')
    okay = checkResult.get('resultType') == 'OK'

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
        'Okay, let\'s start your order', outputContexts=[order_context])


def add_item(request_json: dict):
    dish = request_json.get('queryResult', {}).get('parameters', {}).get(
        'Dish', '')
    if not dish:
        return response('I\'m sorry, I don\'t understand what you wanted')
    order_id = get_context(request_json, '/order').get('orderId')
    order = model.Order(db.document(f'orders/{order_id}'))
    order.items.append(model.OrderItem(dish))
    order.set()
    return response(f'Great, added a {dish} to your order')


def checkout(request_json: dict):
    order_id = get_context(request_json, '/order').get('orderId')
    order = model.Order(db.document(f'orders/{order_id}'))
    prices = {}
    for d in model.AllDishes(db):
        prices[d.name] = d.price
    total = 0
    lineItems = []
    id = 0
    for item in order.items:
        id += 1
        total += prices[item.name]
        lineItems.append({
            'id': str(id),
            'name': item.name,
            'type': 'REGULAR',
            'price': to_price(prices[item.name]),
            'quantity': 1,
        })

    data = payment_data(settings, 'TransactionDecisionValueSpec')
    data['proposedOrder'] = {
        'id': order_id,
        'cart': {
            'merchant': {
                'id': 'serverless-next-demo',
                'name': 'Next Demo'
            },
            'lineItems': lineItems,
        },
        'totalPrice': to_price(total)
    }
    result = {
        'payload': {
            'google': {
                'expectUserResponse': True,
                'systemIntent': {
                    'intent': 'actions.intent.TRANSACTION_DECISION',
                    'data': data
                }
            }
        }
    }
    logging.info(f'Returning {result}')
    return result


def receipt(request_json: dict):
    decision = read_argument(request_json, 'TRANSACTION_DECISION_VALUE')
    logging.info(f'Transaction decision: {decision}')
    okay = decision.get('checkResult', {}).get('resultType') == 'OK'
    accepted = decision.get('userDecision') == 'ORDER_ACCEPTED'
    if not (okay and accepted):
        return response('I\'m sorry. I hope to serverless you again soon.')
    instrument = decision.get('order', {}).get(
        'paymentInfo', {}).get('googleProvidedPaymentInstrument')
    if not instrument:
        return response(
            'Sorry, I couldn\'t read your transaction information.')
    order_id = get_context(request_json, '/order').get('orderId')
    order = model.Order(db.document(f'orders/{order_id}'))
    logging.info(f'Storing token from {instrument}')
    order.token = instrument.get('instrumentToken')
    order.set()
    return response(
        'Thanks for your order. We\'ll get started on it right away!')


HANDLERS = {
    'sale items': sale_items,
    'Default Welcome Intent': welcome,
    'ls': list_menu,
    'buy': start_order,
    'start': validate_payment,
    'add': add_item,
    'checkout': checkout,
    'receipt': receipt,
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
