#!/usr/bin/env python3

# standards
from contextlib import contextmanager
from itertools import count
import re

# canif
from .utils import undefined


NAMED_CONSTANTS = {
    'undefined': undefined,
    'NotImplemented': NotImplemented,
}


BACKSLASH_ESCAPES = {
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

RE_BACKSLASH_ESCAPES = re.compile(
    r'\\(?:%s)' % '|'.join(regex for regex, _ in BACKSLASH_ESCAPES.values())
)


RE_NUMBER = re.compile(r'[\+\-]?\d+(?:\.\d+)?(?:[eE][\+\-]?\d+)?')
RE_BOOL = re.compile(r'(?:[tT]rue|[fF]alse)\b')
RE_NULL = re.compile(r'(?:null|None)\b')
RE_CONSTANT = re.compile(r'|'.join(NAMED_CONSTANTS))
RE_DOUBLE_QUOTED_STRING = re.compile(r'\"((?:[^\\\"]|\\.)*)\"')
RE_SINGLE_QUOTED_STRING = re.compile(r"\'((?:[^\\\']|\\.)*)\'")
RE_REGEX = re.compile(r'/((?:[^\\/]|\\.)*)/(\w*)')
RE_UNQUOTED_KEY = re.compile(r'\$?(?!\d)\w+')
RE_REPR = re.compile(r'<\w+(?:[^\'\">]|"(?:[^\"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')+>')
RE_IDENTIFIER = re.compile(r'\$?(?!\d)\w+')
RE_FUNCTION_CALL = re.compile(r'((?:new\s+)?\w+(?:\.\w+)*)\s*\(')
RE_E_NOTATION = re.compile(r'[\.eE]')


class ParserError(Exception):
    """
    Exception used to signal that the input data does not follow a format that we were able to parse.
    """


class Recorder:
    """
    Lets us buffer to memory calls to Builder methods, for cases where we need to parse ahead a little before we know what builder
    calls to make (unlike most cases, where we call Builder methods immediately as we parse the input).
    """

    def __init__(self, host):
        self._host = host
        self._calls = []

    def __getattr__(self, method_name):
        return lambda *args, **kwargs: self._calls.append((method_name, args, kwargs))

    def playback(self):
        for method_name, args, kwargs in self._calls:
            getattr(self._host, method_name)(*args, **kwargs)


class Parser:
    """
    Uses a Lexer to chop the input into tokens, and then interprets these tokens to build a structural representation of the data.
    Makes calls to `Builder` methods as it discovers the data. Does not store the parsed data in memory.

    In its current implementation this is not written for performance. Maybe someday we'll look into a LEX/YACC sort of solution.
    """

    def __init__(self, lexer, builder):
        self.lexer = lexer
        self.builder = builder

    @contextmanager
    def record_builder_calls(self):
        previous_builder = self.builder  # NB could be nested so this could be another Recorder
        recorder = Recorder(previous_builder)
        self.builder = recorder
        try:
            yield recorder
        finally:
            self.builder = previous_builder

    def _one_of(self, *functions, expected=None):
        for function in functions:
            found = function()
            if found:
                return True
        if expected:
            self.lexer.error(expected)
        return False

    def document(self, include_single_values=False):
        self.builder.open_document()
        if include_single_values:
            self.expression()
        else:
            self._one_of(
                self.square_bracketed_array,
                self.round_bracketed_array,
                self.mapping_or_set,
                self.function_call,
                expected='document',
            )
        return self.builder.close_document()

    def expression(self, checked=False):
        return self._one_of(
            self.square_bracketed_array,
            self.round_bracketed_array,
            self.mapping_or_set,
            self.single_quoted_string,
            self.double_quoted_string,
            self.regex_literal,
            self.number,
            self.bool,
            self.null,
            self.named_constant,
            self.function_call,
            self.identifier,
            self.python_repr_expression,
            expected=('expression' if checked else None),
        )

    def number(self):
        match = self.lexer.pop_regex(RE_NUMBER)
        if match:
            raw = match.group()
            if RE_E_NOTATION.search(raw):
                self.builder.float(raw, float(raw))
            else:
                self.builder.int(raw, int(raw))
            return True

    def bool(self):
        match = self.lexer.pop_regex(RE_BOOL)
        if match:
            raw = match.group()
            value = raw[0].lower() == 't'
            self.builder.bool(raw, value)
            return True

    def null(self):
        match = self.lexer.pop_regex(RE_NULL)
        if match:
            raw = match.group()
            self.builder.null(raw)
            return True

    def named_constant(self):
        match = self.lexer.pop_regex(RE_CONSTANT)
        if match:
            raw = match.group()
            self.builder.named_constant(raw, NAMED_CONSTANTS[raw])
            return True

    def single_quoted_string(self):
        if self.lexer.peek(r"'"):
            match = self.lexer.pop_regex(RE_SINGLE_QUOTED_STRING, checked=True)
            raw = match.group()
            value = self._parse_string_escapes(match.group(1))
            self.builder.string(raw, value)
            return True

    def double_quoted_string(self):
        if self.lexer.peek('"'):
            match = self.lexer.pop_regex(RE_DOUBLE_QUOTED_STRING, checked=True)
            raw = match.group()
            value = self._parse_string_escapes(match.group(1))
            self.builder.string(raw, value)
            return True

    def regex_literal(self):
        # NB we could pass regex literals to `re.compile`, since that's their "parsed" form, but then that would open the door to
        # syntax incompatibilities between Python's regex engine and whatever source we're reading from. That, and we couldn't save
        # the "g" flag. So we save regexes as just a pair of (pattern, flags) strings.
        if self.lexer.peek('/'):
            match = self.lexer.pop_regex(RE_REGEX, checked=True)
            raw = match.group()
            raw_pattern, flags = match.groups()
            value = self._parse_string_escapes(raw_pattern)
            self.builder.regex(raw, value, flags)
            return True

    @staticmethod
    def _parse_string_escapes(raw_text):
        return RE_BACKSLASH_ESCAPES.sub(
            lambda m: BACKSLASH_ESCAPES[m.group()[1]][1](m),  # you're confused, pylint: disable=unnecessary-lambda
            raw_text,
        )

    def unquoted_key(self):
        match = self.lexer.pop_regex(RE_UNQUOTED_KEY)
        if match:
            raw = match.group()
            self.builder.string(raw, raw)
            return True

    def python_repr_expression(self):
        match = self.lexer.pop_regex(RE_REPR)
        if match:
            self.builder.python_repr(match.group())
            return True

    def identifier(self):
        match = self.lexer.pop_regex(RE_IDENTIFIER)
        if match:
            self.builder.identifier(match.group())
            return True

    def square_bracketed_array(self):
        if self.lexer.pop('['):
            self.builder.open_array(list)
            self._comma_separated_list(']', self.builder.array_element, allow_empty_slots=True)
            self.builder.close_array()
            return True

    def round_bracketed_array(self):
        if self.lexer.pop('('):
            self.builder.open_array(tuple)
            self._comma_separated_list(')', self.builder.array_element, needs_at_least_one_comma=True)
            self.builder.close_array()
            return True

    def _comma_separated_list(self, end_token, builder_callback, needs_at_least_one_comma=False, allow_empty_slots=False):
        num_elements = count(1)
        while not self.lexer.peek(end_token):
            if allow_empty_slots and self.lexer.pop(','):
                self.builder.array_empty_slot()
                builder_callback()
            else:
                self.expression(checked=True)
                if self.lexer.peek(',') or self.lexer.peek(end_token):
                    builder_callback()
                if not self.lexer.pop(',', checked=(needs_at_least_one_comma and next(num_elements) == 1)):
                    break
        self.lexer.pop(end_token, checked=True)

    def mapping_or_set(self, checked=False):
        if self.lexer.pop('{', checked):
            if self.lexer.pop('}'):
                # empty mapping
                self.builder.open_mapping()
                self.builder.close_mapping()
            else:
                try:
                    with self.record_builder_calls() as recorder:
                        have_possible_set_element = self._one_of(
                            self.mapping_key,
                            self.expression,
                        )
                except ParserError:
                    # make sure we print back out everything we've consumed
                    self.builder.open_mapping()
                    recorder.playback()
                    raise
                if have_possible_set_element and (self.lexer.pop(',') or self.lexer.peek('}')):
                    self._continue_as_set(recorder)
                else:
                    self._continue_as_mapping(have_possible_set_element, recorder)
            return True

    def _continue_as_set(self, recorder):
        self.builder.open_set()
        recorder.playback()
        self.builder.set_element()
        self._comma_separated_list(
            '}',
            builder_callback=self.builder.set_element,
        )
        self.builder.close_set()

    def _continue_as_mapping(self, first_key_already_parsed, recorder):
        self.builder.open_mapping()
        recorder.playback()
        if not first_key_already_parsed:
            self.mapping_key(checked=True)
        self.lexer.pop(':', checked=True)
        self.builder.mapping_key()
        self.expression(checked=True)
        if self.lexer.pop(','):
            self.builder.mapping_value()
            while not self.lexer.peek('}'):
                self.mapping_key(checked=True)
                self.lexer.pop(':', checked=True)
                self.builder.mapping_key()
                self.expression(checked=True)
                if self.lexer.peek(',') or self.lexer.peek('}'):
                    self.builder.mapping_value()
                if not self.lexer.pop(','):
                    break
        elif self.lexer.peek('}'):
            self.builder.mapping_value()
        self.lexer.pop('}', checked=True)
        self.builder.close_mapping()

    def mapping_key(self, checked=False):
        return self._one_of(
            self.single_quoted_string,
            self.double_quoted_string,
            self.number,
            self.unquoted_key,
            self.round_bracketed_array,
            expected=('key' if checked else None),
        )

    def function_call(self):
        match = self.lexer.pop_regex(RE_FUNCTION_CALL)
        if match:
            function_name = match.group(1)
            self.builder.open_function_call(function_name)
            self._comma_separated_list(
                ')',
                builder_callback=self.builder.function_argument,
            )
            self.builder.close_function_call()
            return True
