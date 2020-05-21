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
    """
    A builder that translates input and pretty-prints it, as JSON.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_commas = False

    def _raw_json(self, json_str):
        self._print(json_str)

    def open_array(self, kind):
        # NB we drop the distinction between lists and tuples
        super().open_array(list)
