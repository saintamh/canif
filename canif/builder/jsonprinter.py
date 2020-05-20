#!/usr/bin/env python3

# canif
from .jsonmixin import PrimitivesAsJsonMixin, StringablesAsJsonMixin, FunctionCallsAsJsonMixin
from .prettyprint import PrettyPrintBuilder


class JsonPrinter(
        PrimitivesAsJsonMixin,
        StringablesAsJsonMixin,
        FunctionCallsAsJsonMixin,
        PrettyPrintBuilder,
        ):

    trailing_commas = False

    def _raw_json(self, json_str):
        self._print(json_str)

    def open_array(self, kind):
        # NB we drop the distinction between lists and tuples
        super().open_array(list)
