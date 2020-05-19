#!/usr/bin/env python3

# canif
from .utils import undefined


class Jsonify:
    """
    Translate native values into a format that is JSON-compatible. This is also
    """

    named_constants = {
        undefined: '$undefined',
        NotImplemented: '$NotImplemented',
    }

    @classmethod
    def named_constant(cls, value):
        return cls.named_constants[value]

    @staticmethod
    def regex(pattern, flags):
        parsed = {'$regex': pattern}
        if flags:
            parsed['$options'] = flags
        return parsed

    @staticmethod
    def python_repr(raw):
        return '$repr%s' % raw

    @staticmethod
    def identifier(name):
        return '$$%s' % name

    @staticmethod
    def collection(kind, value_list):
        if kind is list:
            return value_list
        elif kind is tuple:
            # We just lose the list/tuple distinction
            return list(value_list)
        elif kind is set:
            return {'$set': value_list}
        else:
            raise TypeError(repr(kind))
