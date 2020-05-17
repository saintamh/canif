#!/usr/bin/env python3

# standards
import json
import re

# canif
from .pods import PodsBuilder


class FloatWithoutScientificNotation(float):
    # From https://stackoverflow.com/a/18936966

    def __init__(self, text):
        super().__init__()
        self.__text = text

    def __repr__(self):
        return self.__text


class PrettyPrintBuilder(PodsBuilder):
    """
    A builder that assembles a pretty-printed output, and writes it out.
    """

    float_class = FloatWithoutScientificNotation

    def __init__(self, output, flatten=False, ensure_ascii=False):
        """
        The pretty-printed output will be written to `output`, which should be a writable, text-mode file.

        If `flatten` is True, the output will be printed on one line; if False (the default), it will be pretty-printed on several
        lines.
        """
        self.output = output
        self.flatten = flatten
        self.ensure_ascii = ensure_ascii

    def document(self, expression):
        if self.flatten:
            output_text = json.dumps(expression, sort_keys=True, ensure_ascii=self.ensure_ascii)
        else:
            output_text = self.collapse_short_arrays(
                json.dumps(
                    expression,
                    indent=4,
                    sort_keys=True,
                    ensure_ascii=self.ensure_ascii,
                )
            )
        self.output.write(output_text)

    def named_constant(self, raw, value):
        if value is NotImplemented:
            value = '$NotImplemented'
        return value

    def set(self, elements):
        return {'$set': elements}

    def mapping(self, items):
        for key in list(items.keys()):
            if isinstance(key, tuple):
                # Python tuples as keys
                new_key = '$tuple' + json.dumps(key)
                items[new_key] = items.pop(key)
        return items

    @staticmethod
    def collapse_short_arrays(json_str):
        def collapse(text):
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'("(?:[^\\\"]|\\.)*")|(?<=[\{\[])\ |\ (?=[\}\]])', lambda m: m.group(1) or '', text)
            return text

        return re.sub(
            r'''
            (?: "(?:[^\\\"]|\\.)*"
              | ( [\{\[] (?: "(?:[^\\\"]|\\.)*"
                           | [^\[\{\"\}\]]
                           )+
                  [\]\}] )
              )
        ''',
            lambda m: collapse(m.group(1)) if m.group(1) and len(m.group(1)) < 100 else m.group(0),
            json_str,
            flags=re.X,
        )
