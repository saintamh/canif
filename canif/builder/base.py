#!/usr/bin/env python3


class BuilderError(Exception):
    pass


class Builder:
    """
    `Builder` subclasses define a method for every kind of syntax tree node; the `Parser` takes a `Builder` instance and
    calls those callback methods as the input is parsed. It's then up to to `Builder` to define what to build a tree syntax or
    whatever representation of the AST it needs.
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

    def open_function_call(self):
        raise NotImplementedError

    def function_argument(self):
        raise NotImplementedError

    def close_function_call(self):
        raise NotImplementedError
