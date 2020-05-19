#!/usr/bin/env python3

# standards
import argparse
from io import StringIO
from os import linesep
import re
import sys
from traceback import print_exc

# canif
from .builder import JsonPrinter, VerbatimPrinter
from .lexer import Lexer
from .parser import Parser


def parse_command_line(
        argv,
        default_input_encoding=sys.stdin.encoding,
        default_output_encoding=sys.stdout.encoding
        ):
    parser = argparse.ArgumentParser(description='Pretty-print JSON and JSON-like data')
    indent_group = parser.add_mutually_exclusive_group()
    indent_group.add_argument(
        '-i',
        '--indent',
        type=int,
        default=4,
        help='Indentation level (0 means flattened, single-line output)',
    )
    indent_group.add_argument(
        '-f',
        '--flatten',
        action='store_true',
        help='Flatten output (equivalent to -i 0)',
    )
    parser.add_argument(
        '-j',
        '--json-output',
        action='store_const',
        dest='builder_class',
        const=JsonPrinter,
        default=VerbatimPrinter,
        help='Ensure output is valid JSON (e.g. None becomes null)',
    )
    parser.add_argument(
        '--ensure-ascii',
        action='store_true',
        help=r'Ensure JSON output is ASCII by using \uXXXX sequences in place of non-ASCII characters',
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
        output_buffer = StringIO()
        try:
            lexer = Lexer(input_text)
            builder = options.builder_class(
                output_buffer,
                indent=0 if options.flatten else options.indent,
                ensure_ascii=options.ensure_ascii,
            )
            parser = Parser(lexer, builder)
            parser.document()
            output_text = output_buffer.getvalue()
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
        sys.stdout.buffer.write(output_bytes)
    sys.exit(exit_status)


if __name__ == '__main__':
    main()
