#!/usr/bin/env python3

# canif
from .base import Builder


undefined = object()


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


class FunctionCall:

    special = {
        # https://docs.mongodb.com/manual/reference/mongodb-extended-json/
        #
        # For both $date and $oid there should be a single argument, but don't silently swallow the rest of there are more
        #
        'Date': lambda values: {'$date': values[0] if len(values) == 1 else values},
        'ObjectId': lambda values: {'$oid': values[0] if len(values) == 1 else values},
        'OrderedDict': lambda values: dict(*values),
    }

    def __init__(self, function_name):
        self.function_name = function_name
        self.arguments = []

    def append_argument(self, argument):
        self.arguments.append(argument)

    def build(self):
        operator = self.special.get(self.function_name[2:])
        if operator:
            return operator(self.arguments)
        else:
            return {self.function_name: self.arguments}


class PodsBuilder(Builder):
    """
    A builder that assembles a Plain Old Data Structure (lists, dicts, strings) with the parsed data
    """

    def __init__(self):
        super().__init__()
        self.stack = NotImplemented

    def float(self, raw, value):
        self.stack.append(value)

    def int(self, raw, value):
        self.stack.append(value)

    def named_constant(self, raw, value):
        self.stack.append(value)

    def string(self, raw, value):
        self.stack.append(value)

    def regex(self, raw, pattern, flags):
        parsed = {'$regex': pattern}
        if flags:
            parsed['$options'] = flags
        self.stack.append(parsed)

    def python_repr(self, raw):
        self.stack.append('$repr%s' % raw)

    def identifier(self, name):
        self.stack.append('$$%s' % name)

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

    def open_function_call(self):
        function_name = self.stack.pop()
        function_call = FunctionCall(function_name)
        self.stack.append(function_call)

    def function_argument(self):
        argument = self.stack.pop()
        function_call = self.stack[-1]
        function_call.append_argument(argument)

    def close_function_call(self):
        self._close_collection()
