#!/usr/bin/env python3

# standards
import json
import re


class BuilderError(Exception):
    pass


class FloatWithoutScientificNotation(float):
    # From https://stackoverflow.com/a/18936966

    def __init__(self, text):
        super().__init__()
        self.__text = text

    def __repr__(self):
        return self.__text


class Builder:
    """
    `Builder` subclasses define a method for every kind of syntax tree node; the `Parser` takes a `Builder` instance and
    calls those callback methods as the input is parsed. It's then up to to `Builder` to define what to build a tree syntax or
    whatever representation of the AST it needs.
    """

    def document(self, expression):
        raise NotImplementedError

    def float(self, text):
        raise NotImplementedError

    def int(self, text):
        raise NotImplementedError

    def named_constant(self, text):
        raise NotImplementedError

    def array(self, elements):
        raise NotImplementedError

    def mapping(self, items):
        raise NotImplementedError

    def set(self, elements):
        raise NotImplementedError

    def string(self, text):
        raise NotImplementedError

    def regex(self, pattern, flags):
        raise NotImplementedError

    def python_repr(self, raw_text):
        raise NotImplementedError

    def identifier(self, name):
        raise NotImplementedError

    def function_call(self, function_name, arguments):
        raise NotImplementedError


class PodsBuilder(Builder):
    """
    A builder that assembles a Plain Old Data Structure (lists, dicts, strings) with the parsed data
    """

    float_class = float

    named_constants = {
        'true': True,
        'True': True,
        'false': False,
        'False': False,
        'null': None,
        'None': None,
        'undefined': '$undefined',
        'NotImplemented': NotImplemented,
    }

    special_function_calls = {
        # https://docs.mongodb.com/manual/reference/mongodb-extended-json/
        #
        # For both $date and $oid there should be a single argument, but don't silently swallow the rest of there are more
        #
        'Date': lambda values: {'$date': values[0] if len(values) == 1 else values},
        'ObjectId': lambda values: {'$oid': values[0] if len(values) == 1 else values},
        'OrderedDict': lambda values: dict(*values),
    }

    def document(self, expression):
        return expression

    def float(self, text):
        return self.float_class(text)

    def int(self, text):
        return int(text)

    def named_constant(self, text):
        return self.named_constants[text]

    def array(self, elements):
        return elements

    def mapping(self, items):
        for key in list(items.keys()):
            if isinstance(key, list):
                # Python tuples as keys
                key = json.dumps(key)
        return items

    def set(self, elements):
        return set(elements)

    def string(self, text):
        return text

    def regex(self, pattern, flags):
        parsed = {'$regex': pattern}
        if flags:
            parsed['$options'] = flags
        return parsed

    def python_repr(self, raw_text):
        return '$repr%s' % raw_text

    def identifier(self, name):
        return '$$%s' % name

    def function_call(self, function_name, arguments):
        operator = self.special_function_calls.get(function_name)
        if operator:
            return operator(arguments)
        else:
            return {'$$%s' % function_name: arguments}


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

    def named_constant(self, text):
        normalised = super().named_constant(text)
        if normalised is NotImplemented:
            normalised = '$NotImplemented'
        return normalised

    def set(self, elements):
        return {'$set': elements}

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
