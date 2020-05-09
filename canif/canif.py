#!/usr/bin/env python3

# standards
import argparse
import json
import re
from os import linesep
import sys
from traceback import print_exc

# canif
from .builder import FloatWithoutScientificNotation, Builder
from .lexer import Lexer
from .parser import Parser


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
            lexer = Lexer(input_text)
            builder = Builder()
            parser = Parser(lexer, builder)
            document = parser.document()
            if options.flatten:
                output_text = json.dumps(document, sort_keys=True)
            else:
                output_text = collapse_short_arrays(json.dumps(document, indent=4, sort_keys=True, ensure_ascii=False))
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
