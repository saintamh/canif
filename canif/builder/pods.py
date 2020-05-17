#!/usr/bin/env python3

# canif
from .base import Builder


class PodsBuilder(Builder):
    """
    A builder that assembles a Plain Old Data Structure (lists, dicts, strings) with the parsed data
    """

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

    def float(self, raw, value):
        return value

    def int(self, raw, value):
        return value

    def named_constant(self, raw, value):
        return value

    def string(self, raw, text):
        return text

    def regex(self, raw, pattern, flags):
        parsed = {'$regex': pattern}
        if flags:
            parsed['$options'] = flags
        return parsed

    def python_repr(self, raw):
        return '$repr%s' % raw

    def identifier(self, name):
        return '$$%s' % name

    def array(self, elements):
        return elements

    def tuple(self, elements):
        return elements

    def mapping(self, items):
        return items

    def set(self, elements):
        return set(elements)

    def function_call(self, function_name, arguments):
        operator = self.special_function_calls.get(function_name)
        if operator:
            parsed = operator(arguments)
        else:
            parsed = {'$$%s' % function_name: arguments}
        return parsed
