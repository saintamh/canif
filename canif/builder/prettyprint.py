#!/usr/bin/env python3

# standards
import json
import re

# canif
from .base import Builder


class Token:

    def __init__(self, depth, collapsed_text, expanded_text):
        self.depth = depth
        self.collapsed_text = collapsed_text
        self.expanded_text = expanded_text


class Scope:

    def __init__(self, parent):
        self.parent = parent
        self.depth = parent.depth + 1
        self.queue = []
        self.collapsed_len = 0
        self.could_collapse = True

    def append(self, token):
        self.queue.append(token)
        self.collapsed_len += len(token.collapsed_text)
        indent_len = 2 * self.depth  # FIXME use config for '2'
        max_width = 100  # FIXME read from config
        if indent_len + self.collapsed_len > max_width:
            self.expand()

    def expand(self):
        if self.parent:
            self.parent.expand()
        for token in self.queue:
            print()
            print('  ' * token.depth, end='')  # FIXME read that 2-spaces from config
            print(token.expanded_text)
        self.queue.clear()
        self.could_collapse = False

    def close(self):
        if self.could_collapse:
            


class ArrayScope(Scope):

    def __init__(self, depth):
        super().__init__()
        self.num_elements = 0


class PrettyPrintBuilder(Builder):
    """
    A builder that assembles a pretty-printed output, and writes it out.
    """

    def __init__(self, output, flatten=False, ensure_ascii=False, indent=2):
        """
        The pretty-printed output will be written to `output`, which should be a writable, text-mode file.

        If `flatten` is True, the output will be printed on one line; if False (the default), it will be pretty-printed on several
        lines.
        """
        self.output = output
        self.flatten = flatten
        self.ensure_ascii = ensure_ascii
        self.indent = indent

    def _token(self, scope, text):
        token = Token(scope.depth + 1, text)

    def _indent(self, depth):
        return '\n' + ' ' * self.indent * depth

    def int(self, scope, raw, value):
        return self._token(scope, raw)

    def float(self, scope, raw, value):
        return self._token(scope, raw)

    def named_constant(self, text):
        return self._token(scope, text)

    def string(self, scope, raw, text):
        return self._token(scope, raw)

    def regex(self, scope, raw, pattern, flags):
        return self._token(scope, raw)

    def python_repr(self, scope, raw):
        return self._token(scope, raw)

    def identifier(self, scope, name):
        return self._token(scope, name)

    def open_array(self, scope, kind):
        array = ArrayScope(scope.depth + 1, kind)
        array.queue.append(Token(
            array.depth + 1,
            {list: '[', tuple: '(', set: '{'}[kind],
        ))
        array.flush()
        return array

    def array_element(self, scope, element):
        if scope.num_elements > 0:
            scope.append(Token(
                array.depth + 1,
                collapsed = ', '
                expanded = ',',
            ))
        scope.flush()

    def 

    def mapping(self):
        raise NotImplementedError

    def function_call(self, function_name):
        raise NotImplementedError
