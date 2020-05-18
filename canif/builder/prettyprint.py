#!/usr/bin/env python3

# standards
from os import linesep

# canif
from .pods import PodsBuilder


undefined = object()


class PrettyPrintBuilder(PodsBuilder):
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

    def _end_comma_separated_sequence(self, final_token, length, force_flat_comma=False):
        if self.indent == 0:
            self.spacer = ',' if force_flat_comma else ''
        elif length == 0:
            self.spacer = ''
        else:
            self.spacer = ',' + self._indent_string()
        self._print(final_token)

    def float(self, raw, value):
        self._print(raw)

    def int(self, raw, value):
        self._print(raw)

    def named_constant(self, raw, value):
        self._print(raw)

    def string(self, raw, value):
        self._print(raw)

    def regex(self, raw, pattern, flags):
        self._print(raw)

    def python_repr(self, raw):
        self._print(raw)

    def identifier(self, name):
        self._print(name)

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
            {list: ']', tuple: ')'}[kind],
            length,
            force_flat_comma=(kind is tuple and length == 1),
        )

    def open_mapping_or_set(self):
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
        self._end_comma_separated_sequence('}', length)

    def set_element(self):
        self.spacer = ',' + self._indent_string()
        self._comma_separator()

    def close_set(self):
        length = self.stack.pop()
        self._end_comma_separated_sequence('}', length)

    def open_function_call(self):
        self._print('(')
        self.stack.append(0)
        self.spacer = self._indent_string()

    def function_argument(self):
        self.stack[-1] += 1
        self._comma_separator()

    def close_function_call(self):
        length = self.stack.pop()
        self._end_comma_separated_sequence(')', length)
