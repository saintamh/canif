#!/usr/bin/env python3

# standards
import json
import re


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

    def constant(self, normalised):
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

    def string(self, raw_text):
        return self._unescaped_string(raw_text)

    def regex(self, raw_pattern, flags):
        pattern = self._unescaped_string(raw_pattern)
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

    def _unescaped_string(self, raw_text):
        backslash_escapes = {
            # Using http://json.org/ as a reference
            '\\': (r'\\', lambda m: '\\'),
            '"': (r'"', lambda m: '"'),
            '/': (r'/', lambda m: '/'),
            'b': (r'b', lambda m: '\x08'),
            'f': (r'f', lambda m: '\x0C'),
            'n': (r'n', lambda m: '\n'),
            'r': (r'r', lambda m: '\r'),
            't': (r't', lambda m: '\t'),
            'u': (r'u(?:[0-9a-fA-F]{4})', lambda m: chr(int(m.group()[2:], 16))),
            'x': (r'x(?:[0-9a-fA-F]{2})', lambda m: bytes([int(m.group()[2:], 16)])),
        }
        return re.sub(
            r'\\(?:%s)' % '|'.join(regex for regex, _ in backslash_escapes.values()),
            lambda m: backslash_escapes[m.group()[1]][1](m),  # you're confused, pylint: disable=unnecessary-lambda
            raw_text,
        )


class FloatWithoutScientificNotation(float):
    # From https://stackoverflow.com/a/18936966

    def __init__(self, text):
        super().__init__()
        self.__text = text

    def __repr__(self):
        return self.__text
