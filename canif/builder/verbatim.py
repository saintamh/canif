#!/usr/bin/env python3

# canif
from .prettyprint import PrettyPrintBuilder


undefined = object()


class VerbatimPrinter(PrettyPrintBuilder):

    def _print_array_opening(self, kind):
        self._print({list: '[', tuple: '('}[kind])

    def _print_array_closing(self, kind):
        self._print({list: ']', tuple: ')'}[kind])

    def _print_mapping_opening(self):
        self._print('{')

    def _print_mapping_colon(self):
        self._print(': ')

    def _print_mapping_closing(self):
        self._print('}')

    def _print_set_opening(self):
        self._print('{')

    def _print_set_closing(self):
        self._print('}')

    def _print_function_call_opening(self, function_name):
        self.identifier(function_name)
        self._print('(')

    def _print_function_call_closing(self):
        self._print(')')
