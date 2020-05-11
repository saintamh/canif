#!/usr/bin/env python3


class BuilderError(Exception):
    pass


class Builder:
    """
    `Builder` subclasses define a method for every kind of syntax tree node; the `Parser` takes a `Builder` instance and
    calls those callback methods as the input is parsed. It's then up to to `Builder` to define what to build a tree syntax or
    whatever representation of the AST it needs.
    """

    def float(self, text):
        raise NotImplementedError

    def int(self, text):
        raise NotImplementedError

    def named_constant(self, text):
        raise NotImplementedError

    def string(self, text):
        raise NotImplementedError

    def regex(self, pattern, flags):
        raise NotImplementedError

    def python_repr(self, raw_text):
        raise NotImplementedError

    def identifier(self, name):
        raise NotImplementedError

    def document(self):
        raise NotImplementedError

    def array(self):
        raise NotImplementedError

    def tuple(self):
        raise NotImplementedError

    def set(self):
        raise NotImplementedError

    def mapping(self):
        raise NotImplementedError

    def function_call(self, function_name):
        raise NotImplementedError
