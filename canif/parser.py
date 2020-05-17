#!/usr/bin/env python3

# standards
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

    def _one_of(self, *functions, expected=None):
        for function in functions:
            value = function()
            if value is not undefined:
                return value
        if expected:
            self.lexer.error(expected)
        return undefined

    def document(self):
        document = self.expression(checked=True)
        self.lexer.pop(r'$', checked=True)
        return self.builder.document(document)

    def expression(self, checked=False):
        return self._one_of(
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

    def number(self, checked=False):
        match = self.lexer.pop(r'[\+\-]?\d+(?:\.\d+)?(?:[eE][\+\-]?\d+)?', checked)
        if not match:
            return undefined
        text = match.group()
        if re.search(r'[\.eE]', text):
            return self.builder.float(text, float(text))
        else:
            return self.builder.int(text, int(text))

    def named_constant(self, checked=False):
        match = self.lexer.pop(r'|'.join(self.named_constants), checked)
        if not match:
            return undefined
        raw = match.group()
        return self.builder.named_constant(raw, self.named_constants[raw])

    def single_quoted_string(self, checked=False):
        if not self.lexer.pop(r"'", checked, do_skip=False):
            return undefined
        match = self.lexer.pop(r"((?:[^\\\']|\\.)*)\'", checked=True)
        raw = match.group(1)
        return self.builder.string(raw, self._parse_string_escapes(raw))

    def double_quoted_string(self, checked=False):
        if not self.lexer.pop(r'"', checked, do_skip=False):
            return undefined
        match = self.lexer.pop(r'((?:[^\\\"]|\\.)*)\"', checked=True)
        raw = match.group(1)
        return self.builder.string(raw, self._parse_string_escapes(raw))

    def regex_literal(self, checked=False):
        if not self.lexer.pop(r'/', checked, do_skip=False):
            return undefined
        match = self.lexer.pop(r'((?:[^\\/]|\\.)*)/(\w*)', checked=True)
        raw, flags = match.groups()
        return self.builder.regex(raw, self._parse_string_escapes(raw), flags)

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
        raw = match.group()
        return self.builder.string(raw, raw)

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

    def square_bracketed_array(self, checked=False):
        if not self.lexer.pop(r'\[', checked):
            return undefined
        return self.builder.array(self._array_elements(r'\]'))

    def round_bracketed_array(self, checked=False):
        if not self.lexer.pop(r'\(', checked):
            return undefined
        return self.builder.tuple(tuple(self._array_elements(r'\)')))

    def _array_elements(self, re_end):
        elements = []
        while not self.lexer.peek(re_end):
            elements.append(self.expression(checked=True))
            if not self.lexer.pop(r',', checked=(re_end == r'\)' and len(elements) == 1)):
                break
        self.lexer.pop(re_end, checked=True)
        return elements

    def mapping_or_set(self, checked=False):
        if not self.lexer.pop(r'\{', checked):
            return undefined
        if self.lexer.pop(r'\}'):
            return self.builder.mapping({})
        else:
            value = self._one_of(
                self.mapping_key,
                self.expression,
            )
            if value is not undefined and (self.lexer.pop(r',') or self.lexer.peek(r'\}')):
                return self._set(value)
            else:
                first_key = self.mapping_key(checked=True) if value is undefined else value
                return self._mapping(first_key)

    def _set(self, first_value):
        elements = [first_value]
        while not self.lexer.pop(r'\}'):
            elements.append(self.expression(checked=True))
            if not self.lexer.pop(r','):
                self.lexer.pop(r'\}', checked=True)
                break
        return self.builder.set(elements)

    def _mapping(self, first_key):
        self.lexer.pop(r':', checked=True)
        items = {first_key: self.expression(checked=True)}
        if self.lexer.pop(r','):
            while not self.lexer.peek(r'\}'):
                key = self.mapping_key(checked=True)
                self.lexer.pop(r':', checked=True)
                items[key] = self.expression(checked=True)
                if not self.lexer.pop(r','):
                    break
        self.lexer.pop(r'\}', checked=True)
        return self.builder.mapping(items)

    def mapping_key(self, checked=False):
        return self._one_of(
            self.single_quoted_string,
            self.double_quoted_string,
            self.number,
            self.unquoted_key,
            self.round_bracketed_array,
            expected=('key' if checked else None),
        )

    def function_call(self, checked=False):
        match = self.lexer.pop(r'(?:new\s+)?(\w+(?:\.\w+)*)\s*\(', checked)
        if not match:
            return undefined
        function_name = match.group(1)
        arguments = self._function_arguments()
        return self.builder.function_call(function_name, arguments)

    def _function_arguments(self):
        re_end = r'\)'
        parsed = []
        position_key = lambda index: '_%d' % index
        while not self.lexer.peek(re_end):
            key = self.identifier()
            if key is not undefined:
                # handle Python-style keyword args, e.g. when repr-ing a namedtuple
                if self.lexer.pop(r'='):
                    if isinstance(parsed, list):
                        parsed = {position_key(index): value for index, value in enumerate(parsed)}
                    value = self.expression(checked=True)
                else:
                    value = key
                    key = position_key(len(parsed))
            else:
                key = position_key(len(parsed))
                value = self.expression(checked=True)
            if isinstance(parsed, list):
                parsed.append(value)
            else:
                parsed[key] = value
            if not self.lexer.pop(r','):
                break
        self.lexer.pop(re_end, checked=True)
        return parsed
