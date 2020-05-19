#!/usr/bin/env python3

# standards
import re

# canif
from .parser import ParserError


class Lexer:
    """
    Splits the input text into tokens, i.e. the smallest, indivisible strings in the text.

    Instances of this class keep track of where they are in the text, and advance through it gradually.
    """

    re_skipped = re.compile(r'(?:\s+|//.*)+')

    def __init__(self, text):
        self.text = text
        self.position = 0
        self.skip()

    def skip(self):
        """
        Advance the position past skippable characters in the text (i.e. whitespace and comments)
        """
        match = self.re_skipped.match(self.text, self.position)
        if match:
            self.position = match.end()

    def error(self, expected):
        """
        Raise a `ParserError`. `expected` describes the token that was expected and not found at the current position.
        """
        if not isinstance(expected, str):
            expected = '/%s/' % expected.pattern
        raise ParserError('Position %d: expected %s, found %r' % (
            self.position,
            expected,
            self.text[self.position : self.position + 30],
        ))

    def pop(self, regex, checked=False, do_skip=True):
        """
        Match the text at the current position in the text against the given regex. Returns the regex `Match` object.

        If `checked` is True, raise a `ParserError` if the regex does not match at the current position. If `checked` is False (the
        default) and the regex does not match, return `None`.

        If `do_skip` is True (the default), advance past whitespace (by calling `self.skip()`) after the matching data.
        """
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
        """
        Check whether the text at the current position matches the given regex. Returns the `Match` object if the regex matches,
        `None` if not.
        """
        regex = re.compile(regex)
        return regex.match(self.text, self.position)
