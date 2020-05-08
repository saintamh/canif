#!/usr/bin/env python3

# Reads from stdin data that is either JSON, a JavaScript expression, or Python `repr` output, and spits it back out pretty-printed.

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# standards
import argparse
import json
import re
from os import linesep
import sys
from traceback import print_exc

#----------------------------------------------------------------------------------------------------------------------------------

class Tokenizer:

    re_skipped = re.compile(r'(?:\s+|//.*)+')

    def __init__(self, text):
        self.text = text
        self.position = 0
        self.skip()

    def skip(self):
        match = self.re_skipped.match(self.text, self.position)
        if match:
            self.position = match.end()

    def error(self, expected):
        if not isinstance(expected, str):
            expected = '/%s/' % expected.pattern
        raise ValueError('Expected %s, found %r' % (expected, self.text[self.position : self.position + 30]))

    def pop(self, regex, checked=False, do_skip=True):
        regex = re.compile(regex)
        match = regex.match(self.text, self.position)
        if match:
            self.position = match.end()
            if do_skip:
                self.skip()
        elif checked:
            self.error(regex)
        return match

    def peek(self, regex):
        regex = re.compile(regex)
        return regex.match(self.text, self.position)

#----------------------------------------------------------------------------------------------------------------------------------

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

    def __init__(self, tokens):
        self.tokens = tokens

    def _select(self, expected, *functions):
        empty = object()
        for function in functions:
            value = next(function(), empty)
            if value is not empty:
                return value
        self.tokens.error(expected)

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
        match = self.tokens.pop(r'[\+\-]?\d+(?:\.\d+)?(?:[eE][\+\-]?\d+)?')
        if match:
            text = match.group()
            if re.search(r'[\.eE]', text):
                yield FloatWithoutScientificNotation(text)
            else:
                yield int(text)

    def maybe_constant(self):
        match = self.tokens.pop(r'|'.join(self.constants))
        if match:
            yield self.constants[match.group()]

    def maybe_square_bracketed_array(self):
        if self.tokens.pop(r'\['):
            yield self._array(r'\]')

    def maybe_round_bracketed_array(self):
        if self.tokens.pop(r'\('):
            yield self._array(r'\)')

    def maybe_tuple_as_key(self):
        if self.tokens.pop(r'\('):
            tuple_key = self._array(r'\)')
            yield json.dumps(list(tuple_key))

    def _array(self, re_end):
        parsed = []
        while not self.tokens.peek(re_end):
            parsed.append(self.expression())
            if not self.tokens.pop(r','):
                break
        self.tokens.pop(re_end, checked=True)
        return parsed

    def maybe_object_or_set(self):
        # I still think this is readable, pylint: disable=too-many-nested-blocks
        if self.tokens.pop(r'\{'):
            if self.tokens.peek(r'\}'):
                # empty object
                parsed = {}
            else:
                missing = object()
                value = next(self.maybe_expression(), missing)
                if value is not missing and (self.tokens.pop(r',') or self.tokens.peek(r'\}')):
                    # it's a set
                    parsed = [value]
                    while not self.tokens.peek(r'\}'):
                        parsed.append(self.expression())
                        if not self.tokens.pop(r','):
                            break
                    parsed = {'$set': parsed}
                else:
                    # It's an object. First loop iteration is unrolled because we may (or may not) already have in `value` the
                    # first key expression
                    parsed = {}
                    first_key = self.object_key() if value is missing else value
                    if isinstance(first_key, list):
                        first_key = json.dumps(first_key)
                    self.tokens.pop(r':', checked=True)
                    parsed[first_key] = self.expression()
                    if self.tokens.pop(r','):
                        while not self.tokens.peek(r'\}'):
                            key = self.object_key()
                            self.tokens.pop(r':', checked=True)
                            parsed[key] = self.expression()
                            if not self.tokens.pop(r','):
                                break
            self.tokens.pop(r'\}', checked=True)
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
        if self.tokens.pop(r"'", do_skip=False):
            yield self.unescaped_string(self.tokens.pop(r"((?:[^\\\']|\\.)*)\'", checked=True))

    def maybe_double_quoted_string(self):
        if self.tokens.pop(r'"', do_skip=False):
            yield self.unescaped_string(self.tokens.pop(r'((?:[^\\\"]|\\.)*)\"', checked=True))

    def maybe_regex_literal(self):
        if self.tokens.pop(r'/', do_skip=False):
            match = self.tokens.pop(r'((?:[^\\/]|\\.)*)/(\w*)', checked=True)
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
        match = self.tokens.pop(r'<\w+(?:\.\w+)* object at 0x[0-9a-fA-F]+>')
        if match:
            yield match.group() # make it a string

    def maybe_identifier(self):
        match = self.tokens.pop(r'\$?(?!\d)\w+')
        if match:
            yield match.group()

    def maybe_function_call(self):
        match = self.tokens.pop(r'(?:new\s+)?(\w+(?:\.\w+)*)\s*\(')
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
        while not self.tokens.peek(re_end):
            key = next(self.maybe_identifier(), None)
            if key:
                # handle Python-style keyword args, e.g. when repr-ing a namedtuple
                if self.tokens.pop(r'='):
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
            if not self.tokens.pop(r','):
                break
        self.tokens.pop(re_end, checked=True)
        return parsed


class FloatWithoutScientificNotation(float):
    # From https://stackoverflow.com/a/18936966

    def __init__(self, text):
        super().__init__()
        self.__text = text

    def __repr__(self):
        return self.__text


if hasattr(json.encoder, 'FLOAT_REPR'): # Python 2.7
    json.encoder.FLOAT_REPR = FloatWithoutScientificNotation.__repr__


def collapse_short_arrays(json_str):
    def collapse(text):
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'("(?:[^\\\"]|\\.)*")|(?<=[\{\[])\ |\ (?=[\}\]])', lambda m: m.group(1) or '', text)
        return text

    return re.sub(
        r'''
            (?: "(?:[^\\\"]|\\.)*"
              | ( [\{\[] (?: "(?:[^\\\"]|\\.)*"
                           | [^\[\{\"\}\]]
                           )+
                  [\]\}] )
              )
        ''',
        lambda m: collapse(m.group(1)) if m.group(1) and len(m.group(1)) < 100 else m.group(0),
        json_str,
        flags=re.X,
    )


def parse_command_line(
        argv,
        default_input_encoding=sys.stdin.encoding,
        default_output_encoding=sys.stdout.encoding
        ):
    parser = argparse.ArgumentParser(description='Pretty-print JSON and JSON-like data')
    parser.add_argument(
        '--flatten',
        action='store_true',
        help='Print output on one line (rather than indented',
    )
    parser.add_argument(
        '--json-output',
        action='store_true',
        help='Ensure output is valid JSON (e.g. None becomes null)',
    )
    parser.add_argument(
        '--input-encoding',
        default=default_input_encoding,
        help='Character set used for decoding the input',
    )
    parser.add_argument(
        '--output-encoding',
        default=default_output_encoding,
        help='Character set used for encoding the output',
    )
    return parser.parse_args(argv[1:])


def run(options, input_bytes):
    exit_status = 0
    input_text = input_bytes.decode(options.input_encoding)
    if not input_text.strip():
        output_text = ''
    else:
        try:
            tokens = Tokenizer(input_text)
            parser = Parser(tokens)
            value = parser.expression()
            tokens.pop(r'$', checked=True)
            if options.flatten:
                output_text = json.dumps(value, sort_keys=True)
            else:
                output_text = collapse_short_arrays(json.dumps(value, indent=4, sort_keys=True, ensure_ascii=False))
        except Exception:  # anything at all, pylint: disable=broad-except
            print_exc()
            output_text = input_text
            exit_status = 1
        if output_text:
            output_text = re.sub(r'\s+$', '', output_text, flags=re.MULTILINE) + linesep
    output_bytes = output_text.encode(options.output_encoding)
    return exit_status, output_bytes


def main():
    options = parse_command_line(sys.argv)
    input_bytes = sys.stdin.buffer.read()
    exit_status, output_bytes = run(options, input_bytes)
    if output_bytes:
        sys.stdin.buffer.write(output_bytes)
    sys.exit(exit_status)


if __name__ == '__main__':
    main()

#----------------------------------------------------------------------------------------------------------------------------------
