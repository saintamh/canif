#!/usr/bin/env python3

# standards
from typing import NamedTuple

# 3rd parties
import pytest

# canif
from canif.lexer import Lexer
from canif.parser import Parser, ParserError


class Node(NamedTuple):
    kind: str
    values: tuple

    def __repr__(self):
        return 'AST.%s(%s)' % (self.kind, ', '.join(map(repr, self.values)))


class AstClass:

    def __getattr__(self, node_type):
        return lambda *values: Node(node_type, values)


AST = AstClass()


@pytest.mark.parametrize(
    'input_text, expected',
    [

        # Numbers
        (
            '42',
            AST.int('42'),
        ),
        (
            '3.14',
            AST.float('3.14'),
        ),
        (
            '5.12e-1',
            AST.float('5.12e-1'),
        ),

        # Named constants
        (
            'true',
            AST.named_constant(True),
        ),
        (
            'false',
            AST.named_constant(False),
        ),
        (
            'null',
            AST.named_constant(None),
        ),
        (
            'undefined',
            AST.named_constant({'$undefined': True}),
        ),
        (
            'NotImplemented',
            AST.named_constant('NotImplemented'),
        ),

        # Arrays
        (
            '[1]',
            AST.array([AST.int('1')]),
        ),
        (
            '[1,]',
            AST.array([AST.int('1')]),
        ),
        (
            '[,]',
            ParserError("Expected expression, found ',]'"),
        ),
        (
            '[1,,]',
            ParserError("Expected expression, found ',]'"),
        ),
        (
            '[,1]',
            ParserError("Expected expression, found ',1]'"),
        ),
        (
            '[1, ["a"]]',
            AST.array([AST.int('1'), AST.array([AST.string('a')])]),
        ),

        # Tuples
        (
            '(1,)',
            AST.array([AST.int('1')]),
        ),
        (
            '(1)',
            ParserError("Expected /,/, found ')'"),
        ),
        (
            '(,)',
            ParserError("Expected expression, found ',)'"),
        ),
        (
            '(1,,)',
            ParserError("Expected expression, found ',)'"),
        ),
        (
            '(,1)',
            ParserError("Expected expression, found ',1)'"),
        ),
        (
            '(1, ("a",))',
            AST.array([AST.int('1'), AST.array([AST.string('a')])]),
        ),

        # Mappings
        (
            '{"a": 1}',
            AST.mapping({AST.string('a'): AST.int('1')}),
        ),
        (
            '{"a": 1,}',
            AST.mapping({AST.string('a'): AST.int('1')}),
        ),
        (
            '{"a": 1,,}',
            ParserError("Expected key, found ',}'"),
        ),
        (
            '{,"a": 1}',
            ParserError('Expected key, found \',"a": 1}\''),
        ),
        (
            '{a: 1}',
            AST.mapping({AST.identifier('a'): AST.int('1')}),
        ),

        # Sets
        (
            '{1}',
            AST.set([AST.int('1')]),
        ),
        (
            '{1,}',
            AST.set([AST.int('1')]),
        ),
        (
            '{1,,}',
            ParserError("Expected expression, found ',}'"),
        ),
        (
            '{,1}',
            ParserError("Expected key, found ',1}'"),
        ),
        (
            '{1, 2}',
            AST.set([AST.int('1'), AST.int('2')]),
        ),

        # Single-quoted strings
        (
            '''
                'text'
            ''',
            AST.string('text'),
        ),
        (
            r'''
                'I "love\" this'
            ''',
            AST.string('I "love" this'),
        ),
        (
            r'''
                'It\'s what\'s most'
            ''',
            AST.string("It's what's most"),
        ),
        (
            # NB input is raw string (i.e. the string includes the backslashes), output is not (so is parsed as normal Python
            # strinig literals are)
            r'''
                ' \\ \" \/ \b \f \n \r \t \u0424 \x7E \' '
            ''',
            AST.string(' \\ " / \x08 \x0C \n \r \t Ф ~ \' '),
        ),

        # Double-quoted strings
        (
            '''
                "text"
            ''',
            AST.string('text'),
        ),
        (
            r'''
                "I \"love\" this"
            ''',
            AST.string('I "love" this'),
        ),
        (
            r'''
                "It's what\'s most"
            ''',
            AST.string("It's what's most"),
        ),
        (
            # NB input is raw string (i.e. the string includes the backslashes), output is not (so is parsed as normal Python
            # strinig literals are)
            r'''
                " \\ \" \/ \b \f \n \r \t \u0424 \x7E \' "
            ''',
            AST.string(' \\ " / \x08 \x0C \n \r \t Ф ~ \' '),
        ),

        # Comments
        (
            '''
                36 // thirty-six
            ''',
            AST.int('36'),
        ),
        (
            '''
               // a comment
               "http://not.a.comment/"
            ''',
            AST.string('http://not.a.comment/'),
        ),

        # Python repr expressions
        (
            '<__main__.C object at 0x05b0ace99cf7>',
            AST.python_repr('<__main__.C object at 0x05b0ace99cf7>'),
        ),
        (
            "<re.Match object; span=(0, 1), match='a'>",
            AST.python_repr("<re.Match object; span=(0, 1), match='a'>"),
        ),
        (
            "<dummy match='<>'>",
            AST.python_repr("<dummy match='<>'>"),
        ),

        # Identifiers
        (
            'x',
            AST.identifier('x'),
        ),
        (
            'x10',
            AST.identifier('x10'),
        ),
        (
            'μεταφορά',
            AST.identifier('μεταφορά'),
        ),

        # Function calls
        (
            'x(1)',
            AST.function_call('x', [AST.int('1')]),
        ),
        (
            'x(1,)',
            AST.function_call('x', [AST.int('1')]),
        ),
        (
            'x(1, 2)',
            AST.function_call('x', [AST.int('1'), AST.int('2')]),
        ),

    ]
)
def test_parser(input_text, expected):
    lexer = Lexer(input_text)
    parser = Parser(lexer, AstClass())
    try:
        actual_parse = parser.document()
    except ParserError as actual_error:
        if isinstance(expected, ParserError):
            assert str(actual_error) == str(expected)
        else:
            raise
    else:
        assert actual_parse == expected
