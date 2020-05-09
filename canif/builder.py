#!/usr/bin/env python3

# standards
import json
import re


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
        raise NotImplemented

    def float(self, text):
        raise NotImplemented

    def int(self, text):
        raise NotImplemented

    def named_constant(self, normalised):
        raise NotImplemented

    def array(self, elements):
        raise NotImplemented

    def mapping(self, items):
        raise NotImplemented

    def set(self, elements):
        raise NotImplemented

    def string(self, text):
        raise NotImplemented

    def regex(self, pattern, flags):
        raise NotImplemented

    def python_repr(self, raw_text):
        raise NotImplemented

    def identifier(self, name):
        raise NotImplemented

    def function_call(self, function_name, arguments):
        raise NotImplemented


class PodsBuilder(Builder):
    """
    A builder that assembles a Plain Old Data Structure (lists, dicts, strings) with the parsed data
    """

    float_class = float

    special_function_calls = {
        # https://docs.mongodb.com/manual/reference/mongodb-extended-json/
        'Date': '$date',
        'ObjectId': '$oid',
        'OrderedDict': lambda values: dict(*values),
    }

    def document(self, expression):
        return expression

    def float(self, text):
        return self.float_class(text)

    def int(self, text):
        return int(text)

    def named_constant(self, normalised):
        return normalised

    def array(self, elements):
        return elements

    def mapping(self, items):
        for key in list(items.keys()):
            if isinstance(key, list):
                # Python tuples as keys
                key = json.dumps(key)
        return items

    def set(self, elements):
        return {'$set': elements}

    def string(self, text):
        return text

    def regex(self, pattern, flags):
        parsed = {'$regex': pattern}
        if flags:
            parsed['$options'] = flags
        return parsed

    def python_repr(self, raw_text):
        return raw_text  # make it a string

    def identifier(self, name):
        return name  # make it a string

    def function_call(self, function_name, arguments):
        operator = self.special_function_calls.get(function_name, function_name)
        if callable(operator):
            return operator(arguments)
        else:
            return {operator: arguments}


class PrettyPrintBuilder(PodsBuilder):
    """
    A builder that assembles a pretty-printed output, and writes it out.
    """

    float_class = FloatWithoutScientificNotation

    def __init__(self, output, flatten=False):
        """
        The pretty-printed output will be written to `output`, which should be a writable, text-mode file.

        If `flatten` is True, the output will be printed on one line; if False (the default), it will be pretty-printed on several lines.
        """
        self.output = output
        self.flatten = flatten

    def document(self, expression):
        if self.flatten:
            output_text = json.dumps(expression, sort_keys=True)
        else:
            output_text = self.collapse_short_arrays(json.dumps(expression, indent=4, sort_keys=True, ensure_ascii=False))
        self.output.write(output_text)

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
