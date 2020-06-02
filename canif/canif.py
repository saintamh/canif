#!/usr/bin/env python3

"""
Core top-level functions for this package.
"""

# standards
from os import linesep

# canif
from .builder.pods import PodsBuilder
from .lexer import Lexer
from .parser import Parser


def load(file, **options):
    """
    Read JSON or JSON-ish data structures from `file`, parse them, and build them as Plain Old Data Structures (`dict`, `list`,
    `set` etc).

    `file` should be a text mode file object, open for reading.

    Will raise `ParserError` if a syntax error is encountered.
    """
    return loads(file.read(), **options)


def loads(text, **options):
    """
    Read JSON or JSON-ish data structures from `text`, parse them, and build them as Plain Old Data Structures (`dict`, `list`,
    `set` etc).

    `text` should be a `str`.

    Will raise `ParserError` if a syntax error is encountered.
    """
    lexer = Lexer(text)
    parser = Parser(lexer, PodsBuilder(**options))
    document = parser.document()
    lexer.end(checked=True)
    return document


def translate(builder, input_text, single_document=False):
    """
    Read the given `input_text` and feed it to the given `Builder`, which should print out a translation of the data to its output
    stream. This is what the command-line tool invokes (see `cli.py`).
    """
    lexer = Lexer(input_text)
    parser = Parser(lexer, builder)
    try:
        while not (single_document or lexer.end()):
            parser.document()
            builder.output.write(linesep)
        lexer.end(checked=True)
    except Exception:
        builder.flush()  # finish printing the parsed tokens
        lexer.flush(builder.output)  # then print the unparsed input
        raise
