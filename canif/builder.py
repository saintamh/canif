#!/usr/bin/env python3

# standards
import json


class Builder:
    """
    `Builder` subclasses define a method for every kind of syntax tree node; the `Parser` takes a `Builder` instance and
    calls those callback methods as the input is parsed. It's then up to to `Builder` to define what to build a tree syntax or
    whatever representation of the AST it needs.
    """

    special_function_calls = {
        # https://docs.mongodb.com/manual/reference/mongodb-extended-json/
        'Date': '$date',
        'ObjectId': '$oid',
        'OrderedDict': lambda values: dict(*values),
    }

    def float(self, text):
        return FloatWithoutScientificNotation(text)

    def int(self, text):
        return int(text)

    def named_constant(self, normalised):
        return normalised

    def array(self, elements):
        return elements

    def mapping(self, items):
        for key in list(items.keys()):
            if isinstance(key, list):
                # Python tuples as keys
                key = json.dumps(key)
        return items

    def set(self, elements):
        return {'$set': elements}

    def string(self, text):
        return text

    def regex(self, pattern, flags):
        parsed = {'$regex': pattern}
        if flags:
            parsed['$options'] = flags
        return parsed

    def python_repr(self, raw_text):
        return raw_text  # make it a string

    def identifier(self, name):
        return name  # make it a string

    def function_call(self, function_name, arguments):
        operator = self.special_function_calls.get(function_name, function_name)
        if callable(operator):
            return operator(arguments)
        else:
            return {operator: arguments}


class FloatWithoutScientificNotation(float):
    # From https://stackoverflow.com/a/18936966

    def __init__(self, text):
        super().__init__()
        self.__text = text

    def __repr__(self):
        return self.__text
