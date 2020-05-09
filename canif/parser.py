#!/usr/bin/env python3

# standards
import json
import re


class Parser:

    constants = {
        'true': True,
        'True': True,
        'false': False,
        'False': False,
        'null': None,
        'None': None,
        'undefined': {'$undefined': True},
        'NotImplemented': 'NotImplemented',
    }

    special_function_calls = {
        # https://docs.mongodb.com/manual/reference/mongodb-extended-json/
        'Date': '$date',
        'ObjectId': '$oid',
        'OrderedDict': lambda values: dict(*values),
    }

    def __init__(self, lexer):
        self.lexer = lexer

    def _select(self, expected, *functions):
        empty = object()
        for function in functions:
            value = next(function(), empty)
            if value is not empty:
                return value
        self.lexer.error(expected)

    def expression(self):
        return self._select('expression', self.maybe_expression)

    def maybe_expression(self):
        functions = [
            self.maybe_square_bracketed_array,
            self.maybe_round_bracketed_array,
            self.maybe_object_or_set,
            self.maybe_single_quoted_string,
            self.maybe_double_quoted_string,
            self.maybe_regex_literal,
            self.maybe_number,
            self.maybe_constant,
            self.maybe_function_call,
            self.maybe_python_repr_expression,
        ]
        empty = object()
        for function in functions:
            value = next(function(), empty)
            if value is not empty:
                yield value
                break

    def maybe_number(self):
        match = self.lexer.pop(r'[\+\-]?\d+(?:\.\d+)?(?:[eE][\+\-]?\d+)?')
        if match:
            text = match.group()
            if re.search(r'[\.eE]', text):
                yield FloatWithoutScientificNotation(text)
            else:
                yield int(text)

    def maybe_constant(self):
        match = self.lexer.pop(r'|'.join(self.constants))
        if match:
            yield self.constants[match.group()]

    def maybe_square_bracketed_array(self):
        if self.lexer.pop(r'\['):
            yield self._array(r'\]')

    def maybe_round_bracketed_array(self):
        if self.lexer.pop(r'\('):
            yield self._array(r'\)')

    def maybe_tuple_as_key(self):
        if self.lexer.pop(r'\('):
            tuple_key = self._array(r'\)')
            yield json.dumps(list(tuple_key))

    def _array(self, re_end):
        parsed = []
        while not self.lexer.peek(re_end):
            parsed.append(self.expression())
            if not self.lexer.pop(r','):
                break
        self.lexer.pop(re_end, checked=True)
        return parsed

    def maybe_object_or_set(self):
        # I still think this is readable, pylint: disable=too-many-nested-blocks
        if self.lexer.pop(r'\{'):
            if self.lexer.peek(r'\}'):
                # empty object
                parsed = {}
            else:
                missing = object()
                value = next(self.maybe_expression(), missing)
                if value is not missing and (self.lexer.pop(r',') or self.lexer.peek(r'\}')):
                    # it's a set
                    parsed = [value]
                    while not self.lexer.peek(r'\}'):
                        parsed.append(self.expression())
                        if not self.lexer.pop(r','):
                            break
                    parsed = {'$set': parsed}
                else:
                    # It's an object. First loop iteration is unrolled because we may (or may not) already have in `value` the
                    # first key expression
                    parsed = {}
                    first_key = self.object_key() if value is missing else value
                    if isinstance(first_key, list):
                        first_key = json.dumps(first_key)
                    self.lexer.pop(r':', checked=True)
                    parsed[first_key] = self.expression()
                    if self.lexer.pop(r','):
                        while not self.lexer.peek(r'\}'):
                            key = self.object_key()
                            self.lexer.pop(r':', checked=True)
                            parsed[key] = self.expression()
                            if not self.lexer.pop(r','):
                                break
            self.lexer.pop(r'\}', checked=True)
            yield parsed

    def object_key(self):
        return self._select(
            'key',
            self.maybe_single_quoted_string,
            self.maybe_double_quoted_string,
            self.maybe_number,
            self.maybe_identifier,
            self.maybe_tuple_as_key,
        )

    def maybe_single_quoted_string(self):
        if self.lexer.pop(r"'", do_skip=False):
            yield self.unescaped_string(self.lexer.pop(r"((?:[^\\\']|\\.)*)\'", checked=True))

    def maybe_double_quoted_string(self):
        if self.lexer.pop(r'"', do_skip=False):
            yield self.unescaped_string(self.lexer.pop(r'((?:[^\\\"]|\\.)*)\"', checked=True))

    def maybe_regex_literal(self):
        if self.lexer.pop(r'/', do_skip=False):
            match = self.lexer.pop(r'((?:[^\\/]|\\.)*)/(\w*)', checked=True)
            pattern = self.unescaped_string(match)
            flags = match.group(2)
            parsed = {'$regex': pattern}
            if flags:
                parsed['$options'] = flags
            yield parsed

    def unescaped_string(self, match):
        text = match.group(1)
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
            'x': (r'x(?:[0-9a-fA-F]{2})', lambda m: bytes([int(m.group()[2:], 16)])),
        }
        text = re.sub(
            r'\\(?:%s)' % '|'.join(regex for regex, _ in backslash_escapes.values()),
            lambda m: backslash_escapes[m.group()[1]][1](m),  # you're confused, pylint: disable=unnecessary-lambda
            text,
        )
        return text

    def maybe_python_repr_expression(self):
        match = self.lexer.pop(r'<\w+(?:\.\w+)* object at 0x[0-9a-fA-F]+>')
        if match:
            yield match.group() # make it a string

    def maybe_identifier(self):
        match = self.lexer.pop(r'\$?(?!\d)\w+')
        if match:
            yield match.group()

    def maybe_function_call(self):
        match = self.lexer.pop(r'(?:new\s+)?(\w+(?:\.\w+)*)\s*\(')
        if match:
            function_name = match.group(1)
            parameters = self._function_arguments()
            operator = self.special_function_calls.get(function_name, function_name)
            if callable(operator):
                yield operator(parameters)
            else:
                yield {operator: parameters}

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


class FloatWithoutScientificNotation(float):
    # From https://stackoverflow.com/a/18936966

    def __init__(self, text):
        super().__init__()
        self.__text = text

    def __repr__(self):
        return self.__text
