#!/usr/bin/env python3

# standards
from os import linesep


class PrettyPrintBuilder:
    """
    A builder that assembles a pretty-printed output, and writes it out.
    """

    def __init__(self, output, indent=2, ensure_ascii=False):
        """
        The pretty-printed output will be written to `output`, which should be a writable, text-mode file.

        If `flatten` is True, the output will be printed on one line; if False (the default), it will be pretty-printed on several
        lines.
        """
        super().__init__()
        self.output = output
        self.indent = indent
        self.ensure_ascii = ensure_ascii
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

    def _end_comma_separated_sequence(self, length, force_flat_comma=False):
        if self.indent == 0:
            self.spacer = ',' if force_flat_comma else ''
        elif length == 0:
            self.spacer = ''
        else:
            self.spacer = ',' + self._indent_string()

    def open_document(self):
        pass

    def close_document(self):
        pass

    def open_array(self, kind):
        self._print({list: '[', tuple: '('}[kind])
        self.stack.append([kind, 0])
        self.spacer = self._indent_string()

    def array_element(self):
        self.stack[-1][1] += 1
        self._comma_separator()

    def close_array(self):
        kind, length = self.stack.pop()
        self._end_comma_separated_sequence(
            length,
            force_flat_comma=(kind is tuple and length == 1),
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

    def float(self, raw, value):
        raise NotImplementedError

    def int(self, raw, value):
        raise NotImplementedError

    def bool(self, raw, value):
        raise NotImplementedError

    def null(self, raw):
        raise NotImplementedError

    def named_constant(self, raw, value):
        raise NotImplementedError

    def string(self, raw, value):
        raise NotImplementedError

    def regex(self, raw, pattern, flags):
        raise NotImplementedError

    def python_repr(self, raw):
        raise NotImplementedError

    def identifier(self, name):
        raise NotImplementedError
