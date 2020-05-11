#!/usr/bin/env python3

# canif
from .base import Builder


class Scope:

    def __init__(self):
        self.children = []

    def __len__(self):
        return len(self.children)

    def append(self, child):
        self.children.append(child)

    def close(self):
        raise NotImplementedError


class DocumentScope(Scope):

    def append(self, child):
        assert not self.children, self.children
        super().append(child)

    def close(self):
        assert len(self.children) == 1, self.children
        return self.children[0]


class ArrayScope(Scope):

    def __init__(self, kind):
        assert kind in (list, tuple, set), repr(kind)
        super().__init__()
        self.kind = kind

    def close(self):
        return self.kind(self.children)


class MappingScope(Scope):

    undefined = object()

    def __init__(self):
        super().__init__()
        self.key = self.undefined

    def append(self, child):
        if self.key is self.undefined:
            self.key = child
        else:
            super().append((self.key, child))
            self.key = self.undefined

    def close(self):
        assert self.key is self.undefined, repr(self.key)
        return dict(self.children)


class FunctionCallScope(Scope):

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
        super().__init__()
        self.function_name = function_name

    def close(self):
        operator = self.special.get(self.function_name)
        if operator:
            return operator(self.children)
        else:
            return {'$$%s' % self.function_name: self.children}


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

    def float(self, text):
        return self.float_class(text)

    def int(self, text):
        return int(text)

    def named_constant(self, text):
        return self.named_constants[text]

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

    def document(self):
        return DocumentScope()

    def array(self):
        return ArrayScope(list)

    def tuple(self):
        return ArrayScope(tuple)

    def set(self):
        return ArrayScope(set)

    def mapping(self):
        return MappingScope()

    def function_call(self, function_name):
        return FunctionCallScope(function_name)
