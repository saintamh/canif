#!/usr/bin/env python3

# standards
import re

# canif
from .parser import ParserError


RE_SKIPPED = re.compile(r'(?:\s+|//.*)+')
RE_END = re.compile(r'$')


class Lexer:
    """
    Splits the input text into tokens, i.e. the smallest, indivisible strings in the text.

    Instances of this class keep track of where they are in the text, and advance through it gradually.

    In its current implementation this is not written for performance. Maybe someday we'll look into a LEX/YACC sort of solution.
    """

    def __init__(self, text):
        self.text = text
        self.position = 0
        self.skip()

    def skip(self):
        """
        Advance the position past skippable characters in the text (i.e. whitespace and comments)
        """
        match = RE_SKIPPED.match(self.text, self.position)
        if match:
            self.position = match.end()

    def error(self, expected, message=None):
        """
        Raise a `ParserError`. `expected` describes the token that was expected and not found at the current position.
        """
        if message is None:
            if not isinstance(expected, str):
                expected = '/%s/' % expected.pattern
            elif not re.search(r'^\w+$', expected):
                expected = '`%s`' % expected
            message = 'expected %s, found %r' % (
                expected,
                self.text[self.position : self.position + 30],
            )
        raise ParserError('Position %d: %s' % (self.position, message))

    def pop(self, token, checked=False, do_skip=True, message=None):
        """
        Match the text at the current position in the text against the given token (a `str`). Returns a boolean indicating whether a
        match was found.

        If `checked` is True, raise a `ParserError` rather than returning `False` when no match is false.

        If `do_skip` is True (the default), advance past whitespace (by calling `self.skip()`) after the matching data.
        """
        if self.text.startswith(token, self.position):
            self.position += len(token)
            if do_skip:
                self.skip()
            return True
        elif checked:
            self.error(token, message)
        else:
            return False

    def pop_regex(self, regex, checked=False, do_skip=True, message=None):
        """
        Same as `pop`, but accepts a regex instead of a plain string token. Returns `None` if `checked` is False (the default) and
        no match is found, else returns the `Match object.
        """
        match = regex.match(self.text, self.position)
        if match:
            self.position = match.end()
            if do_skip:
                self.skip()
        elif checked:
            self.error(regex, message)
        return match

    def peek(self, token):
        """
        Returns a boolean indicating whether the text at the current position starts with the given `token`.
        """
        return self.text.startswith(token, self.position)

    def peek_regex(self, regex):
        """
        Same as `peek`, but accepts a regex instead of a plain string token.
        """
        regex = re.compile(regex)
        return regex.match(self.text, self.position)

    def end(self, checked=False):
        return self.pop_regex(RE_END, checked=checked)

    def flush(self, file_out):
        """
        Writes to the given file object whatever was left unconsumed in our input data.
        """
        file_out.write(self.text[self.position:])
