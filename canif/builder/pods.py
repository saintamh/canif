#!/usr/bin/env python3

# standards
import json

# canif
from .base import Builder


class PodsBuilder(Builder):
    """
    A builder that assembles a Plain Old Data Structure (lists, dicts, strings) with the parsed data
    """

    float_class = float

    named_constants = {
        'true': True,
        'True': True,
        'false': False,
        'False': False,
        'null': None,
        'None': None,
        'undefined': '$undefined',
        'NotImplemented': NotImplemented,
    }

    special_function_calls = {
        # https://docs.mongodb.com/manual/reference/mongodb-extended-json/
        #
        # For both $date and $oid there should be a single argument, but don't silently swallow the rest of there are more
        #
        'Date': lambda values: {'$date': values[0] if len(values) == 1 else values},
        'ObjectId': lambda values: {'$oid': values[0] if len(values) == 1 else values},
        'OrderedDict': lambda values: dict(*values),
    }

    def document(self, expression):
        return expression

    def float(self, text):
        return self.float_class(text)

    def int(self, text):
        return int(text)

    def named_constant(self, text):
        return self.named_constants[text]

    def array(self, elements):
        return elements

    def tuple(self, elements):
        return elements

    def mapping(self, items):
        for key in list(items.keys()):
            if isinstance(key, list):
                # Python tuples as keys
                key = json.dumps(key)
        return items

    def set(self, elements):
        return set(elements)

    def string(self, text):
        return text

    def regex(self, pattern, flags):
        parsed = {'$regex': pattern}
        if flags:
            parsed['$options'] = flags
        return parsed

    def python_repr(self, raw_text):
        return '$repr%s' % raw_text

    def identifier(self, name):
        return '$$%s' % name

    def function_call(self, function_name, arguments):
        operator = self.special_function_calls.get(function_name)
        if operator:
            return operator(arguments)
        else:
            return {'$$%s' % function_name: arguments}
