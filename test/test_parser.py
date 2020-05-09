#!/usr/bin/env python3

# 3rd parties
import pytest

# canif
from canif.builder import Builder
from canif.lexer import Lexer
from canif.parser import Parser


class AST(Builder):
    """
    A dummy builder that just builds an abstract syntax tree such that we can reconstruct how the callbacks were called
    """

    class Node:

        def __init__(self, value):
            self.value = value

        def __eq__(self, other):
            # NB the type comparison is important here because we want e.g. `string(42) != regex(42)`
            return type(self) is type(other) and self.value == other.value

    # We use lowercase names to save on boilerplate, else we'd need a `class Mapping` and then a `def mapping()` that just does
    # `return Mapping()`. This keeps things concise, so forgive us, pylint: disable=invalid-name

    class float(Node):
        pass

    class int(Node):
        pass

    class named_constant(Node):
        pass

    class array(Node):
        pass

    class mapping(Node):
        pass

    class set(Node):
        pass

    class string(Node):
        pass

    class regex(Node):
        def __init__(self, pattern, flags):
            super().__init__([pattern, flags])

    class python_repr(Node):
        pass

    class identifier(Node):
        pass

    class function_call(Node):
        pass


@pytest.mark.parametrize(
    'input_text, expected_parse',
    [
        (
            '42',
            AST.int('42'),
        ),
        # TestCase(
        #     input='3.14',
        #     json_output='3.14',
        #     echo_output='3.14',
        #     pods_output=3.14,
        # ),
        # TestCase(
        #     input='5.12e-1',
        #     json_output='5.12e-1',
        #     echo_output='5.12e-1',
        #     pods_output=0.512,
        # ),
    ]
)
def test_parser(input_text, expected_parse):
    lexer = Lexer(input_text)
    parser = Parser(lexer, AST())
    actual_parse = parser.document()
    assert actual_parse == expected_parse
