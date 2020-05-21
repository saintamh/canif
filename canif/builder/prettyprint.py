#!/usr/bin/env python3

# standards
from os import linesep


class PrettyPrintBuilder:
    """
    Abstract base class for builders that translate input and pretty-print it out, without keeping it in memory.
    """

    def __init__(self, output, indent=4, ensure_ascii=False, trailing_commas=True):
        """
        The pretty-printed output will be written to `output`, which should be a writable, text-mode file.
        """
        super().__init__()
        self.output = output
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        self.trailing_commas = trailing_commas
        self.stack = []
        self.spacer = None

    def _print(self, text):
        if self.spacer:
            self.output.write(self.spacer)
            self.spacer = None
        self.output.write(text)

    def _indent_string(self):
        if self.indent == 0:
            return ''
        depth = self.indent * len(self.stack)
        return linesep + ' ' * depth

    def _comma_separator(self):
        if self.indent:
            self.spacer = ',' + self._indent_string()
        else:
            self.spacer = ', '

    def _end_comma_separated_sequence(self, length, force_comma=False):
        if self.indent == 0:
            self.spacer = ',' if force_comma else ''
        elif length == 0:
            self.spacer = ''
        else:
            self.spacer = (',' if force_comma or self.trailing_commas else '') + self._indent_string()

    def open_document(self):
        pass

    def close_document(self):
        pass

    def open_array(self, kind):
        self._print({list: '[', tuple: '('}[kind])
        self.stack.append([kind, 0, -1])
        self.spacer = self._indent_string()

    def array_element(self):
        self.stack[-1][1] += 1
        self.stack[-1][2] -= 1
        self._comma_separator()

    def close_array(self):
        kind, length, count_since_empty_slot = self.stack.pop()
        self._end_comma_separated_sequence(
            length,
            force_comma=(
                count_since_empty_slot == 0  # array ends in empty slot
                or (kind is tuple and length == 1)
            ),
        )
        self._print({list: ']', tuple: ')'}[kind])

    def open_mapping(self):
        self._print('{')
        self.stack.append(0)
        self.spacer = self._indent_string()

    def mapping_key(self):
        self._print(': ')

    def mapping_value(self):
        self.stack[-1] += 1
        self._comma_separator()

    def close_mapping(self):
        length = self.stack.pop()
        self._end_comma_separated_sequence(length)
        self._print('}')

    def flush(self):
        if self.spacer:
            self.output.write(self.spacer.rstrip())
