#!/usr/bin/env python3

"""
Defines the command-line interface for canif. This is what gets run when `canif` is invoked on the command line.
"""

# standards
import argparse
import sys

# canif
from .builder import JsonPrinter, VerbatimPrinter
from .canif import translate
from .parser import ParserError


def parse_command_line(
        argv,
        default_input_encoding=sys.stdin.encoding,
        default_output_encoding=sys.stdout.encoding
        ):
    parser = argparse.ArgumentParser(description='Pretty-print JSON and JSON-ish data')
    indent_group = parser.add_mutually_exclusive_group()
    indent_group.add_argument(
        '-i',
        '--indent',
        type=int,
        default=4,
        metavar='N',
        help='Indent each level by N spaces (0 means flat, single-line output)',
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
        help="Convert data to valid JSON if it wasn't already (e.g. None becomes null)",
    )
    parser.add_argument(
        '-T',
        '--no-trailing-commas',
        action='store_false',
        dest='trailing_commas',
        default=True,
        help="Don't insert trailing commas after the last item in a sequence. This is implied by --json-output.",
    )
    parser.add_argument(
        '--single-document',
        action='store_true',
        help='Check that the input consists of a single document, rather that the default of accepting a stream of documents',
    )
    parser.add_argument(
        '--ensure-ascii',
        action='store_true',
        help=r'Ensure JSON output is ASCII by using \uXXXX sequences in place of non-ASCII characters',
    )
    parser.add_argument(
        '-I',
        '--input-encoding',
        default=default_input_encoding,
        metavar='ENCODING',
        help='Character set used for decoding the input (default: %s)' % default_input_encoding.upper(),
    )
    parser.add_argument(
        '-O',
        '--output-encoding',
        default=default_output_encoding,
        metavar='ENCODING',
        help='Character set used for encoding the output (default: %s)' % default_output_encoding.upper(),
    )
    return parser.parse_args(argv[1:])


def main():
    options = parse_command_line(sys.argv)
    input_bytes = sys.stdin.buffer.read()
    input_text = input_bytes.decode(options.input_encoding)
    builder = options.builder_class(
        sys.stdout,
        indent=0 if options.flatten else options.indent,
        ensure_ascii=options.ensure_ascii,
        trailing_commas=options.trailing_commas
    )
    try:
        translate(builder, input_text, single_document=options.single_document)
    except ParserError as error:
        print('ParserError: %s' % error, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
