"""Main website for Serverless food ordering.

The site contains views for both customer and staff order management, as
well as Google Sign In for both.
"""

import flask
import simplejson
import logging
import os
from google.auth.transport import requests
from google.oauth2 import id_token
from google.cloud import firestore

from model import model

# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.
app = flask.Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60
db = firestore.Client()
settings = {}


def read_jwt_token(req):
    """Extract the information from a JWT token."""
    if os.getenv('FLASK_ENV', '') == 'development':
        return {'sub': '1234'}
    if not settings:
        initialize()
    app.logger.info('Checking auth for "%s"' % req.headers['Authorization'])
    jwt = req.headers['Authorization'].split(' ').pop()
    auth_request = requests.Request()
    app.logger.info('Checking JWT "%s"' % jwt)
    id_info = id_token.verify_oauth2_token(jwt, auth_request,
                                           settings['client_id'])
    if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
        raise AssertionError(
            'Got a token for the wrong issuer! (%s)' % id_info['iss'])
    return id_info


@app.route('/')
def show_login():
    """Show the login page."""
    data = {'clientid': settings['client_id']}
    app.logger.info("rendering with %s", data)
    return flask.render_template('login.html', clientid=settings['client_id'])


@app.route('/orders')
def show_my_orders():
    """Show the currently logged-in user's orders."""
    user = read_jwt_token(flask.request)
    app.logger.info('Reading orders for %s', user['sub'])
    orders = model.UserOrders(db, user['sub'])
    data = [{'id': user['sub']}]
    data.extend(orders)
    return simplejson.dumps(data, for_json=True, indent=2)

@app.route('/chef')
def show_todo_orders():
    """Show any orders not yet marked done."""
    orders = [x for x in model.OpenOrders(db)]
    orders.sort(key=lambda x: x.date.ToDatetime().timestamp())
    app.logger.info('Orders are: %s', orders)
    return flask.render_template('chef.html', orders=orders)


@app.route('/static/<path:path>')
def serve_static(path):
    return flask.send_from_directory('static', path, cache_timeout=60)


@app.before_first_request
def initialize():
    app.logger.setLevel(logging.INFO)
    client_id = os.getenv('CLIENT_ID', '')
    if not client_id:
        config = db.document('config/app').get()
        client_id = config.get('client_id')
    app.logger.info("Using OAuth client id '%s'", client_id)
    settings['client_id'] = client_id


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    if not CLIENT_ID:
        config = db.document('config/app').get()
        CLIENT_ID = config.get('client_id')
    print("Using OAuth client id '%s'" % CLIENT_ID)

    app.run(host='127.0.0.1', port=8080, debug=True)
