#!/usr/bin/env python3


class BuilderError(Exception):
    pass


class Builder:
    """
    `Builder` subclasses define a method for every kind of syntax tree node; the `Parser` takes a `Builder` instance and
    calls those callback methods as the input is parsed. It's then up to to `Builder` to define what to build a tree syntax or
    whatever representation of the AST it needs.
    """

    def document(self, expression):
        raise NotImplementedError

    def float(self, raw, value):
        raise NotImplementedError

    def int(self, raw, value):
        raise NotImplementedError

    def named_constant(self, raw, value):
        raise NotImplementedError

    def string(self, raw, text):
        raise NotImplementedError

    def regex(self, raw, pattern, flags):
        raise NotImplementedError

    def python_repr(self, raw):
        raise NotImplementedError

    def identifier(self, name):
        raise NotImplementedError

    def array(self, elements):
        raise NotImplementedError

    def tuple(self, elements):
        raise NotImplementedError

    def mapping(self, items):
        raise NotImplementedError

    def set(self, elements):
        raise NotImplementedError

    def function_call(self, function_name, arguments):
        raise NotImplementedError
