"""Function to perform background processing of Firestore updates."""

from google.cloud import firestore

db = firestore.Client()

def onUpdate(data, context):
    """Reconcile changes to a Firestore order object."""
    doc = db.document(context.resource)
    value = doc.get().to_dict()

    if 'done' not in value:
      value['done'] = False
    
    if value != data['oldvalue']
      # Need to update the object
      doc.set(value)