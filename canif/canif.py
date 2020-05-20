#!/usr/bin/env python3

# standards
import argparse
from os import linesep
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


def run(options, input_bytes, output=sys.stdout):
    input_text = input_bytes.decode(options.input_encoding)
    lexer = Lexer(input_text)
    builder = options.builder_class(
        output,
        indent=0 if options.flatten else options.indent,
        ensure_ascii=options.ensure_ascii,
    )
    parser = Parser(lexer, builder)
    try:
        while not lexer.peek(r'$'):
            parser.document()
            output.write(linesep)
        return 0
    except Exception:  # anything at all, pylint: disable=broad-except
        builder.flush()  # finish printing the parsed tokens
        lexer.flush(output)  # then print the unparsed input
        print_exc()
        return 1


def main():
    options = parse_command_line(sys.argv)
    input_bytes = sys.stdin.buffer.read()
    exit_status = run(options, input_bytes)
    sys.exit(exit_status)


if __name__ == '__main__':
    main()
