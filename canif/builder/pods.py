#!/usr/bin/env python3

# canif
from .base import Builder
from .jsonmixin import FunctionCallsAsJsonMixin, StringablesAsJsonMixin
from ..utils import undefined


class Collection:

    def __init__(self, kind):
        self.kind = kind
        self.elements = []

    def append(self, element):
        self.elements.append(element)

    def build(self):
        return self.kind(self.elements)


class Mapping:

    def __init__(self):
        self.items = {}
        self.key = undefined

    def add_key(self, key):
        assert self.key is undefined, repr(self.key)
        self.key = key

    def add_value(self, value):
        assert self.key is not undefined
        self.items[self.key] = value
        self.key = undefined

    def build(self):
        assert self.key is undefined, repr(self.key)
        return self.items


class PodsBuilder(StringablesAsJsonMixin, FunctionCallsAsJsonMixin, Builder):
    """
    A builder that assembles a Plain Old Data Structure (lists, dicts, strings) with the parsed data. Loads it all to memory, and
    then returns it.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stack = NotImplemented

    def float(self, raw, value):
        self.stack.append(value)

    def int(self, raw, value):
        self.stack.append(value)

    def bool(self, raw, value):
        self.stack.append(value)

    def null(self, raw):
        self.stack.append(None)

    def named_constant(self, raw, value):
        self.stack.append(value)

    def string(self, raw, value):
        self.stack.append(value)

    def open_document(self):
        assert self.stack is NotImplemented, repr(self.stack)
        self.stack = []

    def close_document(self):
        assert len(self.stack) == 1, self.stack
        value = self.stack.pop()
        self.stack = NotImplemented
        return value

    def open_array(self, kind):
        self.stack.append(Collection(kind))

    def array_element(self):
        element = self.stack.pop()
        collection = self.stack[-1]
        collection.append(element)

    def _close_collection(self):
        collection = self.stack.pop()
        value = collection.build()
        self.stack.append(value)

    def close_array(self):
        self._close_collection()

    def open_mapping(self):
        self.stack.append(Mapping())

    def mapping_key(self):
        key = self.stack.pop()
        mapping = self.stack[-1]
        mapping.add_key(key)

    def mapping_value(self):
        value = self.stack.pop()
        mapping = self.stack[-1]
        mapping.add_value(value)

    def close_mapping(self):
        self._close_collection()

    def open_set(self):
        self.stack.append(Collection(set))

    def set_element(self):
        element = self.stack.pop()
        collection = self.stack[-1]
        collection.append(element)

    def close_set(self):
        self._close_collection()

    def flush(self):
        pass  # we don't print out anything
