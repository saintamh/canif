#!/usr/bin/env python3


class Builder:
    """
    `Builder` subclasses define a method for every event that the parser encounters as it navigates the tree of the input data. The
    `Parser` takes a `Builder` instance and calls those callback methods as the input is parsed. It's then up to to `Builder` to
    define what to build a tree syntax or whatever representation of the AST it needs.
    """

    def float(self, raw, value):
        raise NotImplementedError

    def int(self, raw, value):
        raise NotImplementedError

    def bool(self, raw, value):
        raise NotImplementedError

    def null(self, raw):
        raise NotImplementedError

    def named_constant(self, raw, value):
        raise NotImplementedError

    def string(self, raw, value):
        raise NotImplementedError

    def regex(self, raw, pattern, flags):
        raise NotImplementedError

    def python_repr(self, raw):
        raise NotImplementedError

    def identifier(self, name):
        raise NotImplementedError

    def open_document(self):
        raise NotImplementedError

    def close_document(self):
        raise NotImplementedError

    def open_array(self, kind):
        raise NotImplementedError

    def array_element(self):
        raise NotImplementedError

    def array_empty_slot(self):
        raise NotImplementedError

    def close_array(self):
        raise NotImplementedError

    def open_mapping(self):
        raise NotImplementedError

    def mapping_key(self):
        raise NotImplementedError

    def mapping_value(self):
        raise NotImplementedError

    def close_mapping(self):
        raise NotImplementedError

    def open_set(self):
        raise NotImplementedError

    def set_element(self):
        raise NotImplementedError

    def close_set(self):
        raise NotImplementedError

    def open_function_call(self, function_name):
        raise NotImplementedError

    def function_call_positional_argument(self):
        raise NotImplementedError

    def function_call_end_positional_arguments(self):
        raise NotImplementedError

    def function_call_start_keyword_arguments(self):
        raise NotImplementedError

    def function_call_keyword_argument_key(self):
        raise NotImplementedError

    def function_call_keyword_argument_value(self):
        raise NotImplementedError

    def function_call_end_keyword_arguments(self):
        raise NotImplementedError

    def close_function_call(self):
        raise NotImplementedError

    def flush(self):
        raise NotImplementedError
