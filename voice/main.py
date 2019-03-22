from flask import Flask, request
import json
import random

app = Flask(__name__)


def sale_items(request_json):
    quote = request_json['queryResult'].get('fulfillmentText', 'Nothing')
    return dict(fulfillmentText='I said "%s"' % quote)


def welcome(request_json):
    OPTS = ['How may I serve you today?',
            'It\'s a great day for a demo.',
            'What can I get for you?']
    return dict(fulfillmentText=random.choice(OPTS))


HANDLERS = {
    'sale items': sale_items,
    'Default Welcome Intent': welcome,
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


@app.route("/", methods=['POST'])
def default():
    data = request.get_json()
    app.logger.info("Got message:\n%s", json.dumps(
        data, indent=2, sort_keys=True))
    response = build_response(data)
    return json.dumps(response)


@app.route("/", methods=['GET'])
def info():
    return '<!doctype html><html><body>This is the app!</body></html>'
