#!/usr/bin/env python3

# standards
from itertools import count
import re


class ParserError(ValueError):
    pass


undefined = object()


class Parser:

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

    def __init__(self, lexer, builder):
        self.lexer = lexer
        self.builder = builder

    def _one_of(self, parent, *functions, expected=None):
        for function in functions:
            value = function(parent)
            if value is not undefined:
                return value
        if expected:
            self.lexer.error(expected)
        return undefined

    def document(self):
        document = self.builder.open_document()
        expression = self.expression(document, checked=True)
        self.lexer.pop(r'$', checked=True)
        return self.builder.close_document(document)

    def expression(self, parent, checked=False):
        return self._one_of(
            parent,
            self.square_bracketed_array,
            self.round_bracketed_array,
            self.mapping_or_set,
            self.single_quoted_string,
            self.double_quoted_string,
            self.regex_literal,
            self.number,
            self.named_constant,
            self.function_call,
            self.identifier,
            self.python_repr_expression,
            expected=('expression' if checked else None),
        )

    def number(self, parent, checked=False):
        match = self.lexer.pop(r'[\+\-]?\d+(?:\.\d+)?(?:[eE][\+\-]?\d+)?', checked)
        if not match:
            return undefined
        text = match.group()
        if re.search(r'[\.eE]', text):
            return self.builder.float(parent, text, float(text))
        else:
            return self.builder.int(parent, text, int(text))

    def named_constant(self, parent, checked=False):
        match = self.lexer.pop(r'|'.join(self.named_constants), checked)
        if not match:
            return undefined
        return self.builder.named_constant(
            parent,
            match.group(),
            self.named_constant[match.group()],
        )

    def square_bracketed_array(self, parent, checked=False):
        if not self.lexer.pop(r'\[', checked):
            return undefined
        array = self.open_array(parent, list)
        return self._comma_separated_list(r'\]', array)

    def round_bracketed_array(self, parent, checked=False):
        if not self.lexer.pop(r'\(', checked):
            return undefined
        array = self.open_array(parent, tuple)
        return self._comma_separated_list(r'\)', array, needs_at_least_one_comma=True)

    def _comma_separated_list(self, re_end, array, needs_at_least_one_comma=False):
        num_elements = count(1)
        while not self.lexer.peek(re_end):
            element = self.expression(array, checked=True)
            self.builder.array_element(array, element)
            if not self.lexer.pop(r',', checked=(needs_at_least_one_comma and next(num_elements) == 1)):
                break
        self.lexer.pop(re_end, checked=True)
        return self.builder.close_array(array)

    def mapping_or_set(self, parent, checked=False):
        if not self.lexer.pop(r'\{', checked):
            return undefined
        if self.lexer.pop(r'\}'):
            # it's an empty mapping
            mapping = self.builder.open_mapping(parent)
            return self.builder.close_mapping(mapping)
        else:
            value = self._one_of(
                parent,
                self.mapping_key,
                self.expression,
            )
            if value is not undefined and (self.lexer.pop(r',') or self.lexer.peek(r'\}')):
                # it's a set
                array = self.builder.open_array(parent, set)
                self.builder.array_element(array, value)
                return self._comma_separated_list(r'\}', array)
            else:
                # it's a mapping
                mapping = self.builder.mapping()
                builder.mapping_key(mapping, value)
                return self._mapping_items(mapping)

    def _mapping_items(self, mapping):
        self.lexer.pop(r':', checked=True)
        self.builder.mapping_value(mapping, self.expression(mapping, checked=True))
        if self.lexer.pop(r','):
            while not self.lexer.peek(r'\}'):
                self.builder.mapping_key(mapping, self.mapping_key(mapping, checked=True))
                self.lexer.pop(r':', checked=True)
                self.builder.mapping_value(mapping, self.expression(mapping, checked=True))
                if not self.lexer.pop(r','):
                    break
        self.lexer.pop(r'\}', checked=True)
        return self.builder.close_mapping(mapping)

    def mapping_key(self, checked=False):
        return self._one_of(
            self.single_quoted_string,
            self.double_quoted_string,
            self.number,
            self.unquoted_key,
            self.round_bracketed_array,
            expected=('key' if checked else None),
        )

    def single_quoted_string(self, checked=False):
        if not self.lexer.pop(r"'", checked, do_skip=False):
            return undefined
        match = self.lexer.pop(r"((?:[^\\\']|\\.)*)\'", checked=True)
        return self.builder.string(
            "'" + match.group(),
            self._parse_string_escapes(match.group(1)),
        )

    def double_quoted_string(self, checked=False):
        if not self.lexer.pop(r'"', checked, do_skip=False):
            return undefined
        match = self.lexer.pop(r'((?:[^\\\"]|\\.)*)\"', checked=True)
        return self.builder.string(
            '"' + match.group(),
            self._parse_string_escapes(match.group(1)),
        )

    def regex_literal(self, checked=False):
        if not self.lexer.pop(r'/', checked, do_skip=False):
            return undefined
        match = self.lexer.pop(r'((?:[^\\/]|\\.)*)/(\w*)', checked=True)
        raw_pattern, flags = match.groups()
        return self.builder.regex(
            '/' + match.group(),
            self._parse_string_escapes(raw_pattern),
            flags,
        )

    @staticmethod
    def _parse_string_escapes(raw_text):
        backslash_escapes = {
            # Using http://json.org/ as a reference
            '\\': (r'\\', lambda m: '\\'),
            '"': (r'"', lambda m: '"'),
            '/': (r'/', lambda m: '/'),
            'b': (r'b', lambda m: '\x08'),
            'f': (r'f', lambda m: '\x0C'),
            'n': (r'n', lambda m: '\n'),
            'r': (r'r', lambda m: '\r'),
            't': (r't', lambda m: '\t'),
            'u': (r'u(?:[0-9a-fA-F]{4})', lambda m: chr(int(m.group()[2:], 16))),
            'x': (r'x(?:[0-9a-fA-F]{2})', lambda m: chr(int(m.group()[2:], 16))),
            # Not strict JSON
            "'": (r"'", lambda m: "'"),
        }
        return re.sub(
            r'\\(?:%s)' % '|'.join(regex for regex, _ in backslash_escapes.values()),
            lambda m: backslash_escapes[m.group()[1]][1](m),  # you're confused, pylint: disable=unnecessary-lambda
            raw_text,
        )

    def unquoted_key(self, checked=False):
        match = self.lexer.pop(r'\$?(?!\d)\w+', checked)
        if not match:
            return undefined
        return self.builder.string(match.group(), match.group())

    def python_repr_expression(self, checked=False):
        match = self.lexer.pop(r'<\w+(?:[^\'\">]|"(?:[^\"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')+>', checked)
        if not match:
            return undefined
        return self.builder.python_repr(match.group())

    def identifier(self, checked=False):
        match = self.lexer.pop(r'\$?(?!\d)\w+', checked)
        if not match:
            return undefined
        return self.builder.identifier(match.group())

    def function_call(self, checked=False):
        match = self.lexer.pop(r'(?:new\s+)?(\w+(?:\.\w+)*)\s*\(', checked)
        if not match:
            return undefined
        function_name = match.group(1)
        return self._comma_separated_list(r'\)', self.builder.function_call(function_name))
