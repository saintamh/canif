#!/usr/bin/env python3

# canif
from .prettyprint import PrettyPrintBuilder


class VerbatimPrinter(PrettyPrintBuilder):
    # Those are from the superclass interface, pylint: disable=unused-argument

    def float(self, raw, value):
        self._print(raw)

    def int(self, raw, value):
        self._print(raw)

    def bool(self, raw, value):
        self._print(raw)

    def null(self, raw):
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

    def array_empty_slot(self):
        self.stack[-1][2] = 1
        self._print('')

    def open_set(self):
        self._print('{')
        self.stack.append(0)
        self.spacer = self._indent_string()

    def set_element(self):
        self.spacer = ',' + self._indent_string()
        self.stack[-1] += 1
        self._comma_separator()

    def close_set(self):
        length = self.stack.pop()
        self._end_comma_separated_sequence(length)
        self._print('}')

    def open_function_call(self, function_name):
        self.identifier(function_name)
        self._print('(')
        self.stack.append(0)
        self.spacer = self._indent_string()

    def function_call_positional_argument(self):
        self.stack[-1] += 1
        self._comma_separator()

    def function_call_end_positional_arguments(self):
        pass

    def function_call_start_keyword_arguments(self):
        pass

    def function_call_keyword_argument_key(self):
        self._print('=')

    def function_call_keyword_argument_value(self):
        self.stack[-1] += 1
        self._comma_separator()

    def function_call_end_keyword_arguments(self):
        pass

    def close_function_call(self):
        length = self.stack.pop()
        self._end_comma_separated_sequence(length)
        self._print(')')
