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

    @property
    def ingredients(self):
        """Yields a list of Ingredient objects for this dish."""
        ingredients = self._ref.collection('ingredients')
        for item in ingredients.stream():
            yield Ingredient(item)


class Ingredient:
    def __init__(self, ref_or_snapshot):
        doc = _materialize_ref_if_needed(ref_or_snapshot)
        data = doc.to_dict()

        self.name = doc.id
        self.max_items = data.get('max', 0)
        self.choices = data.get('names')
        self.price = data.get('charge', 0)


class OrderItem:
    def __init__(self, item=None, **kwds):
        self.name = item
        self.choices = kwds

    def get_price(self, pricing_map: dict):
        price = pricing_map[self.name]
        for items in self.choices.values():
            for item in items:
                if item in pricing_map:
                    price += pricing_map[item]
        return price

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
        self.date = data.update_time
        self.items = []
        raw = data.to_dict() or {}
        logging.info('Data from %s is %s', self.__ref, raw)
        logging.info('Path is %s (%s)', '/'.join(self.__ref._path),
                     type(self.__ref))
        logging.info('Reading path: %s', self.__ref.path)
        self.user = raw.pop('user', '0')
        self.done = raw.pop('done', False)
        self.token = raw.pop('token', {})
        self.total = raw.pop('totalPrice', None)
        for item in raw.pop('items', []):
            self.items.append(OrderItem(**item))
        self.extra_fields = raw

    @property
    def ref(self):
        return self.__ref

    @property
    def path(self):
        return self.__ref.path

    def updateTotal(self, price_map: dict):
        total = 0
        for item in self.items:
            total += item.get_price(price_map)
        self.total = total

    def for_json(self):
        return {
            'id': self.id,
            'items': self.items,
            'user': self.user,
            'done': self.done,
            'date': self.date.ToJsonString(),
            'totalPrice': self.total,
            # Don't show token in rendered JSON!
        }

    def as_dict(self):
        base = {
            'user': self.user,
            'done': self.done,
            'items': [x.as_dict() for x in self.items],
            'token': self.token,
            'totalPrice': self.total,
        }
        base.update(self.extra_fields)
        return base

    def set(self):
        data = self.as_dict()
        logging.info('Writing %s', data)
        self.__ref.set(data)


def AllDishes(db):
    return (Dish(x) for x in db.collection('dishes').get())


def PriceSheet(dishes):
    price_sheet = {}
    for dish in dishes:
        price_sheet[dish.name] = dish.price
        for category in dish.ingredients:
            if category.price:
                for item in category.choices:
                    price_sheet[item] = category.price
    return price_sheet


def OpenOrders(db):
    return (Order(x)
            for x in db.collection('orders').where('done', '==', False).get())


def UserOrders(db, user):
    return (Order(x)
            for x in db.collection('orders').where('user', '==', user).get())
