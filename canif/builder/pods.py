#!/usr/bin/env python3

# canif
from .base import Builder


undefined = object()


class DocumentScope:

    def __init__(self):
        self.expression = undefined

    def set_expression(self, expression):
        assert self.expression is undefined, repr(self.expression)
        self.expression = expression

    def close(self):
        assert self.expression is not undefined
        return self.expression


class ArrayScope:

    def __init__(self, kind):
        assert kind in (list, tuple, set), repr(kind)
        self.kind = kind
        self.elements = []

    def insert(self, element):
        self.elements.append(element)

    def close(self):
        return self.kind(self.elements)


class MappingScope:

    def __init__(self):
        self.items = {}
        self.key = undefined

    def insert_key(self, key):
        assert self.key is undefined, repr(self.key)
        self.key = key

    def insert_value(self, value):
        assert self.key is not undefined
        self.items[self.key] = value
        self.key = undefined

    def close(self):
        assert self.key is self.undefined, repr(self.key)
        return self.items


class FunctionCallScope:

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

    def insert_argument(self, argument):
        self.arguments.append(argument)

    def close(self):
        operator = self.special.get(self.function_name)
        if operator:
            return operator(self.arguments)
        else:
            return {'$$%s' % self.function_name: self.arguments}


class PodsBuilder(Builder):
    """
    A builder that assembles a Plain Old Data Structure (lists, dicts, strings) with the parsed data
    """

    float_class = float

    def int(self, scope, raw, value):
        return value

    def float(self, scope, raw, value):
        return value

    def named_constant(self, scope, raw, value):
        return value

    def string(self, scope, raw, text):
        return text

    def regex(self, scope, raw, pattern, flags):
        parsed = {'$regex': pattern}
        if flags:
            parsed['$options'] = flags
        return parsed

    def python_repr(self, scope, raw):
        return '$repr%s' % raw

    def identifier(self, scope, name):
        return '$$%s' % name

    def open_document(self):
        return DocumentScope()

    def set_document_expression(self, scope, expression):
        scope.set_expression(expression)

    def close_document(self, scope):
        return scope.close()

    def open_array(self, scope, kind):
        return ArrayScope(kind)

    def insert_array_element(self, scope, element):
        scope.append(element)

    def close_array(self, scope):
        return scope.close()

    def open_mapping(self, scope):
        return MappingScope()

    def insert_mapping_key(self, scope, key):
        scope.insert_key(key)

    def insert_mapping_value(self, scope, value):
        scope.insert_value(value)

    def open_function_call(self, scope, function_name):
        return FunctionCallScope(function_name)

    def insert_function_call_argument(self, scope, argument):
        scope.insert_argument(argument)

    def close_function_call(self, scope):
        return scope.close()
