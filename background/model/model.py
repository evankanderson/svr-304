"""Data model for Serverless Ordering Platform.

The model contains ORM classes for managing the Firestore documents which make
up the database backend for the Serverless Ordering Platform. Each data model
object has a constructor which takes either a DocumentReference or a
DocumentSnapshot. If a DocumentReference is provided, the data object will
call .get() to fetch a copy. Generally, this will be as efficient as feeding
the object from .get() into the model, except in cases where you want to reuse
the dictionary.
"""

import logging

from google.cloud import firestore


def _materialize_ref_if_needed(ref_or_snapshot):
    """Return a DocumentSnapshot, given a ref or a snapshot."""
    if isinstance(ref_or_snapshot, firestore.DocumentReference):
        return ref_or_snapshot.get()
    return ref_or_snapshot


class Dish:
    def __init__(self, ref_or_snapshot):
        data = _materialize_ref_if_needed(ref_or_snapshot)

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
        data = _materialize_ref_if_needed(ref_or_snapshot)

        self.name = data.id
        self.max_items = data.get('max')
        self.choices = data.get('names')
        self.price = data.to_dict().get('charge', 0)


class OrderItem:
    def __init__(self, item=None, **kwds):
        self.name = item
        self.choices = kwds

    def for_json(self):
        value = {'item': self.name}
        value.update(self.choices)
        return value

    def as_dict(self):
        value = {'item': self.name}
        value.update(self.choices)
        return value


class Order:
    def __init__(self, ref_or_snapshot):
        data = _materialize_ref_if_needed(ref_or_snapshot)

        self.id = data.reference.id
        self.__ref = data.reference
        self.items = []
        raw = data.to_dict() or {}
        logging.info('Data from %s is %s', self.__ref, raw)
        logging.info('Path is %s (%s)', '/'.join(self.__ref._path), type(self.__ref))
        logging.info('Reading path: %s', self.__ref.path)
        self.user = raw.get('user', '0')
        self.done = raw.get('done', False)
        for item in raw.get('items', []):
            self.items.append(OrderItem(**item))

    @property
    def ref(self):
        return self.__ref

    @property
    def path(self):
        return self.__ref.path

    def for_json(self):
        return {
            'id': self.id,
            'items': self.items,
            'user': self.user,
            'done': self.done
        }

    def as_dict(self):
        return {
            'user': self.user,
            'done': self.done,
            'items': [x.as_dict() for x in self.items]
        }

    def set(self):
        data = self.as_dict()
        logging.info('Writing %s', data)
        self.__ref.set(data)


def AllDishes(db):
    return (Dish(x) for x in db.collection('dishes').get())


def OpenOrders(db):
    return (Order(x)
            for x in db.collection('orders').where('done', '!=', 'True').get())


def UserOrders(db, user):
    return (Order(x)
            for x in db.collection('orders').where('user', '==', user).get())
