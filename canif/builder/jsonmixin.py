#!/usr/bin/env python3

# standards
import json

# canif
from ..utils import undefined


# These mixins are specifically meant to extend `Builder`, and so the methods they implement override that classes' own, why is
# why we have arguments we don't use, but I understand you're confised, pylint: disable=unused-argument


class PrimitivesAsJsonMixin:
    """
    Translate native values into a format that is JSON-compatible. This is also
    """

    named_constants = {
        undefined: '$undefined',
        NotImplemented: '$NotImplemented',
    }

    def _raw_json(self, json_str):
        raise NotImplementedError

    def _dumps(self, value):
        return json.dumps(value, ensure_ascii=self.ensure_ascii)

    def float(self, raw, value):
        self._raw_json(self._dumps(value))

    def int(self, raw, value):
        self._raw_json(self._dumps(value))

    def bool(self, raw, value):
        self._raw_json(self._dumps(value))

    def null(self, raw):
        self._raw_json('null')

    def named_constant(self, raw, value):
        self.string(value, self.named_constants[value])

    def string(self, raw, value):
        self._raw_json(self._dumps(value))

    def open_set(self):
        self.open_mapping()
        self.string(None, '$set')
        self.mapping_key()
        self.open_array(list)

    def set_element(self):
        self.array_element()

    def close_set(self):
        self.close_array()
        self.mapping_value()
        self.close_mapping()


class StringablesAsJsonMixin:

    def __init__(self, *args, identifier_prefix='$$', **kwargs):
        super().__init__(*args, **kwargs)
        self.identifier_prefix = identifier_prefix

    def identifier(self, name):
        self.string(name, '%s%s' % (self.identifier_prefix, name))

    def regex(self, pattern, flags):
        self.open_mapping()
        self.string(None, '$regex')
        self.mapping_key()
        self.string(None, pattern)
        self.mapping_value()
        if flags:
            self.string(None, '$options')
            self.mapping_key()
            self.string(None, flags)
            self.mapping_value()
        self.close_mapping()

    def python_repr(self, raw):
        self.string(raw, '$repr%s' % raw)

    def array_empty_slot(self):
        self.null(None)


class FunctionCallsAsJsonMixin:

    special = {
        # https://docs.mongodb.com/manual/reference/mongodb-extended-json/
        #
        # For both $date and $oid there should be a single argument, but don't silently swallow the rest of there are more
        #
        'Date': '$date',
        'ObjectId': '$oid',
    }

    def open_function_call(self, function_name):
        self.open_mapping()
        self.string(None, self.special.get(function_name, '%s%s' % (self.identifier_prefix, function_name)))
        self.mapping_key()
        self.open_array(list)

    def function_call_positional_argument(self):
        self.array_element()

    def function_call_end_positional_arguments(self):
        self.close_array()
        self.mapping_value()

    def function_call_start_keyword_arguments(self):
        self.string(None, '$kwargs')
        self.mapping_key()
        self.open_mapping()

    def function_call_keyword_argument_key(self):
        self.mapping_key()

    def function_call_keyword_argument_value(self):
        self.mapping_value()

    def function_call_end_keyword_arguments(self):
        self.close_mapping()
        self.mapping_value()

    def close_function_call(self):
        self.close_mapping()
