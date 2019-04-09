"""Function to perform background processing of Firestore updates.

To deploy, try something like:

$ gcloud functions deploy background --runtime python37 \
    --trigger-event providers/cloud.firestore.eventTypes/document.write \
    --trigger-resource projects/$PROJECT_ID/databases/(default)/documents/orders/{order}
"""

import logging
import time
from google.cloud import firestore

from model import model

db = firestore.Client()


def background(data, context):
    """Reconcile changes to a Firestore order object."""
    url = context.resource
    path = url[url.find('/documents/') + len('/documents/'):]
    logging.info('Loading %s (%s)', url, path)
    doc = db.document(path).get()
    if not doc.exists:
        logging.info('Ignoring deleted document %s', path)
        return
    order = model.Order(doc)

    if not order.done and order.token:
        time.sleep(40)
        order.done = True

    if order.as_dict() != doc.to_dict():
        logging.info('Updating %s', order.ref.path)
        order.set()
