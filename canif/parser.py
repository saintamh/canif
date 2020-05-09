#!/usr/bin/env python3

# standards
import re


class ParserError(ValueError):
    pass


class Parser:

    named_constants = {
        'true': True,
        'True': True,
        'false': False,
        'False': False,
        'null': None,
        'None': None,
        'undefined': {'$undefined': True},
        'NotImplemented': 'NotImplemented',
    }

    def __init__(self, lexer, builder):
        self.lexer = lexer
        self.builder = builder

    def _select(self, expected, *functions):
        undefined = object()
        for function in functions:
            value = next(function(), undefined)
            if value is not undefined:
                return value
        self.lexer.error(expected)

    def document(self):
        document = self.expression()
        self.lexer.pop(r'$', checked=True)
        return document

    def expression(self):
        return self._select('expression', self.maybe_expression)

    def maybe_expression(self):
        functions = [
            self.maybe_square_bracketed_array,
            self.maybe_round_bracketed_array,
            self.maybe_mapping_or_set,
            self.maybe_single_quoted_string,
            self.maybe_double_quoted_string,
            self.maybe_regex_literal,
            self.maybe_number,
            self.maybe_named_constant,
            self.maybe_function_call,
            self.maybe_identifier,
            self.maybe_python_repr_expression,
        ]
        undefined = object()
        for function in functions:
            value = next(function(), undefined)
            if value is not undefined:
                yield value
                break

    def maybe_number(self):
        match = self.lexer.pop(r'[\+\-]?\d+(?:\.\d+)?(?:[eE][\+\-]?\d+)?')
        if match:
            text = match.group()
            if re.search(r'[\.eE]', text):
                yield self.builder.float(text)
            else:
                yield self.builder.int(text)

    def maybe_named_constant(self):
        match = self.lexer.pop(r'|'.join(self.named_constants))
        if match:
            yield self.builder.named_constant(self.named_constants[match.group()])

    def maybe_square_bracketed_array(self):
        if self.lexer.pop(r'\['):
            yield self._array(r'\]')

    def maybe_round_bracketed_array(self):
        if self.lexer.pop(r'\('):
            yield self._array(r'\)')

    def _array(self, re_end):
        parsed = []
        while not self.lexer.peek(re_end):
            parsed.append(self.expression())
            if not self.lexer.pop(r',', checked=(re_end == r'\)' and len(parsed) == 1)):
                break
        self.lexer.pop(re_end, checked=True)
        return self.builder.array(parsed)

    def maybe_mapping_or_set(self):
        if self.lexer.pop(r'\{'):
            if self.lexer.pop(r'\}'):
                yield self.builder.mapping({})
            else:
                undefined = object()
                value = next(self.maybe_expression(), undefined)
                if value is not undefined and (self.lexer.pop(r',') or self.lexer.peek(r'\}')):
                    yield self._finish_set(value)
                else:
                    first_key = self.mapping_key() if value is undefined else value
                    yield self._finish_mapping(first_key)

    def _finish_set(self, first_value):
        elements = [first_value]
        while not self.lexer.pop(r'\}'):
            elements.append(self.expression())
            if not self.lexer.pop(r','):
                self.lexer.pop(r'\}', checked=True)
                break
        return self.builder.set(elements)

    def _finish_mapping(self, first_key):
        self.lexer.pop(r':', checked=True)
        items = {first_key: self.expression()}
        if self.lexer.pop(r','):
            while not self.lexer.peek(r'\}'):
                key = self.mapping_key()
                self.lexer.pop(r':', checked=True)
                items[key] = self.expression()
                if not self.lexer.pop(r','):
                    break
        self.lexer.pop(r'\}', checked=True)
        return self.builder.mapping(items)

    def mapping_key(self):
        return self._select(
            'key',
            self.maybe_single_quoted_string,
            self.maybe_double_quoted_string,
            self.maybe_number,
            self.maybe_identifier,
            self.maybe_round_bracketed_array,
        )

    def maybe_single_quoted_string(self):
        if self.lexer.pop(r"'", do_skip=False):
            match = self.lexer.pop(r"((?:[^\\\']|\\.)*)\'", checked=True)
            yield self.builder.string(self._parse_string_escapes(match.group(1)))

    def maybe_double_quoted_string(self):
        if self.lexer.pop(r'"', do_skip=False):
            match = self.lexer.pop(r'((?:[^\\\"]|\\.)*)\"', checked=True)
            yield self.builder.string(self._parse_string_escapes(match.group(1)))

    def maybe_regex_literal(self):
        if self.lexer.pop(r'/', do_skip=False):
            match = self.lexer.pop(r'((?:[^\\/]|\\.)*)/(\w*)', checked=True)
            raw_pattern, flags = match.groups()
            yield self.builder.regex(self._parse_string_escapes(raw_pattern), flags)

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

    def maybe_python_repr_expression(self):
        match = self.lexer.pop(r'<\w+(?:[^\'\">]|"(?:[^\"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')+>')
        if match:
            yield self.builder.python_repr(match.group())

    def maybe_identifier(self):
        match = self.lexer.pop(r'\$?(?!\d)\w+')
        if match:
            yield self.builder.identifier(match.group())

    def maybe_function_call(self):
        match = self.lexer.pop(r'(?:new\s+)?(\w+(?:\.\w+)*)\s*\(')
        if match:
            yield self.builder.function_call(
                match.group(1),
                self._function_arguments(),
            )

    def _function_arguments(self):
        re_end = r'\)'
        parsed = []
        position_key = lambda index: '_%d' % index
        while not self.lexer.peek(re_end):
            key = next(self.maybe_identifier(), None)
            if key:
                # handle Python-style keyword args, e.g. when repr-ing a namedtuple
                if self.lexer.pop(r'='):
                    if isinstance(parsed, list):
                        parsed = {position_key(index): value for index, value in enumerate(parsed)}
                    value = self.expression()
                else:
                    value = key
                    key = position_key(len(parsed))
            else:
                key = position_key(len(parsed))
                value = self.expression()
            if isinstance(parsed, list):
                parsed.append(value)
            else:
                parsed[key] = value
            if not self.lexer.pop(r','):
                break
        self.lexer.pop(re_end, checked=True)
        return parsed
