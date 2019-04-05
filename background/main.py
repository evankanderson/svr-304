"""Function to perform background processing of Firestore updates.

To deploy, try something like:

$ gcloud functions deploy background --runtime python37 \
    --trigger-event providers/cloud.firestore.eventTypes/document.write \
    --trigger-resource projects/$PROJECT_ID/databases/(default)/documents/orders/{order}
"""

import logging
from google.cloud import firestore

from model import model

db = firestore.Client()


def background(data, context):
    """Reconcile changes to a Firestore order object."""
    url = context.resource
    path = url[url.find('/documents/') + len('/documents/'):]
    logging.info('loading %s (%s)', url, path)
    doc = db.document(path).get()
    order = model.Order(doc)

    if order.as_dict() != doc.to_dict():
        logging.info('Updating %s', order.ref.path)
        order.set()
