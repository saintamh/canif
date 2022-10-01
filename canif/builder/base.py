#!/usr/bin/env python3

# standards
from abc import ABC, abstractmethod


class Builder(ABC):
    """
    `Builder` subclasses define a method for every event that the parser encounters as it navigates the tree of the input data. The
    `Parser` takes a `Builder` instance and calls those callback methods as the input is parsed. It's then up to to `Builder` to
    define what to build a tree syntax or whatever representation of the AST it needs.
    """

    @abstractmethod
    def float(self, raw, value):
        ...

    @abstractmethod
    def int(self, raw, value):
        ...

    @abstractmethod
    def bool(self, raw, value):
        ...

    @abstractmethod
    def null(self, raw):
        ...

    @abstractmethod
    def named_constant(self, raw, value):
        ...

    @abstractmethod
    def string(self, raw, value):
        ...

    @abstractmethod
    def regex(self, raw, pattern, flags):
        ...

    @abstractmethod
    def python_repr(self, raw):
        ...

    @abstractmethod
    def identifier(self, name):
        ...

    @abstractmethod
    def open_document(self):
        ...

    @abstractmethod
    def close_document(self):
        ...

    @abstractmethod
    def open_array(self, kind):
        ...

    @abstractmethod
    def array_element(self):
        ...

    @abstractmethod
    def array_empty_slot(self):
        ...

    @abstractmethod
    def close_array(self):
        ...

    @abstractmethod
    def open_mapping(self):
        ...

    @abstractmethod
    def mapping_key(self):
        ...

    @abstractmethod
    def mapping_value(self):
        ...

    @abstractmethod
    def close_mapping(self):
        ...

    @abstractmethod
    def open_set(self):
        ...

    @abstractmethod
    def set_element(self):
        ...

    @abstractmethod
    def close_set(self):
        ...

    @abstractmethod
    def open_function_call(self, function_name):
        ...

    @abstractmethod
    def function_call_positional_argument(self):
        ...

    @abstractmethod
    def function_call_end_positional_arguments(self):
        ...

    @abstractmethod
    def function_call_start_keyword_arguments(self):
        ...

    @abstractmethod
    def function_call_keyword_argument_key(self):
        ...

    @abstractmethod
    def function_call_keyword_argument_value(self):
        ...

    @abstractmethod
    def function_call_end_keyword_arguments(self):
        ...

    @abstractmethod
    def close_function_call(self):
        ...

    @abstractmethod
    def flush(self):
        ...
