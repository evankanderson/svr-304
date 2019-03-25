"""Data model for Serverless Ordering Platform.

The model contains ORM classes for managing the Firestore documents which make
up the database backend for the Serverless Ordering Platform. Each data model
object has a constructor which takes either a DocumentReference or a
DocumentSnapshot. If a DocumentReference is provided, the data object will
call .get() to fetch a copy. Generally, this will be as efficient as feeding
the object from .get() into the model, except in cases where you want to reuse
the dictionary.
"""

from google.cloud import firestore


def __materialize_ref_if_needed(ref_or_snapshot):
    """Return a DocumentSnapshot, given a ref or a snapshot."""
    if isinstance(ref_or_snapshot, firestore.DocumentReference):
        return ref_or_snapshot.get()


class Dish:
    def __init__(self, ref_or_snapshot):
        data = __materialize_ref_if_needed(ref_or_snapshot)

        self.name = data.id
        self.price = data.get('price')
        self._ref = data.reference

    def ingredients(self):
        """Yields a list of Ingredient objects for this dish."""
        ingredients = self._ref.collection('ingredients')
        for item in ingredients.stream():
            yield Ingredient(item)


class Ingredient:
    def __init__(self, ref_or_snapshot):
        data = __materialize_ref_if_needed(ref_or_snapshot)

        self.name = data.id
        self.max_items = data.get('max')
        self.choices = data.get('names')
        self.price = data.to_dict().get('charge', 0)


class OrderItem:
    def __init__(self, item=None, **kwds):
        self.name = item
        self.choices = kwds

    def as_dict(self):
        value = {'item': self.name}
        value.update(self.choices)
        return value


class Orders:
    def __init__(self, ref_or_snapshot):
        data = __materialize_ref_if_needed(ref_or_snapshot)

        self.id = data.id
        self.__ref = data.reference
        self.items = []
        raw = data.to_dict()
        self.user = raw.get('user', '0')
        self.done = raw.get('done', False)
        for item in raw.get('items', []):
            self.items.append(OrderItem(**item))

    def set(self):
        data = {
            'user': self.user,
            'done': self.done,
            'items': [x.as_dict() for x in self.items]
        }
        self.__ref.set(data)
