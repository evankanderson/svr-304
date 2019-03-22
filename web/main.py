"""Main website for Serverless food ordering.

The site contains views for both customer and staff order management, as
well as Google Sign In for both.
"""

import flask
import os
from google.auth.transport import requests
from google.oauth2 import id_token
from google.cloud import firestore

# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.
app = flask.Flask(__name__)
db = firestore.Client()
CLIENT_ID = os.getenv('CLIENT_ID', 'next-svr304-2019')


def read_jwt_token(jwt):
    """Extract the information from a JWT token."""
    request = requests.Request()
    id_info = id_token.verify_oauth2_token(jwt, request, CLIENT_ID)
    if id_info['iss'] != 'https://accounts.google.com':
        raise AssertionError('Got a token for the wrong issuer!')
    return id_info


@app.route('/')
def show_login():
    """Show the login page."""
    return flask.render_template('login.html', clientid=CLIENT_ID)


@app.route('/orders')
def show_my_orders():
    """Show the currently logged-in user's orders."""
    jwt = flask.request.headers['Authorization'].split(' ').pop()
    user = read_jwt_token(jwt)
    orders = db.collection('orders').where('user', '==', id_info['sub']).get()
    return flask.render_template('orders.html', orders=orders)


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
