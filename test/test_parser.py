#!/usr/bin/env python3

# standards
from typing import NamedTuple

# 3rd parties
import pytest

# canif
from canif.lexer import Lexer
from canif.parser import Parser, ParserError


class AstNode(NamedTuple):
    kind: str
    values: tuple

    def __repr__(self):
        return 'AST.%s(%s)' % (self.kind, ', '.join(map(repr, self.values)))


class AstClass:
    """
    Stand-in for the `Builder` class. The parser will call the various Builder methods on this (`int`, `text`, etc), we just create
    in each call an `AstNode` that records what parameters were passed to the method. That way we can test the parser separately
    from the Builder.
    """

    def __getattr__(self, node_kind):
        return lambda *values: AstNode(node_kind, values)


AST = AstClass()


class Case(NamedTuple):
    input_text: str
    expected_parse: AstNode


@pytest.mark.parametrize(
    ','.join(Case._fields),
    [

        # Numbers
        Case(
            '42',
            expected_parse=AST.int('42'),
        ),
        Case(
            '3.14',
            expected_parse=AST.float('3.14'),
        ),
        Case(
            '5.12e-1',
            expected_parse=AST.float('5.12e-1'),
        ),

        # Named constants
        Case(
            'true',
            expected_parse=AST.named_constant(True),
        ),
        Case(
            'false',
            expected_parse=AST.named_constant(False),
        ),
        Case(
            'null',
            expected_parse=AST.named_constant(None),
        ),
        Case(
            'undefined',
            expected_parse=AST.named_constant({'$undefined': True}),
        ),
        Case(
            'NotImplemented',
            expected_parse=AST.named_constant('NotImplemented'),
        ),

        # Arrays
        Case(
            '[1]',
            expected_parse=AST.array([AST.int('1')]),
        ),
        Case(
            '[1,]',
            expected_parse=AST.array([AST.int('1')]),
        ),
        Case(
            '[,]',
            expected_parse=ParserError("Expected expression, found ',]'"),
        ),
        Case(
            '[1,,]',
            expected_parse=ParserError("Expected expression, found ',]'"),
        ),
        Case(
            '[,1]',
            expected_parse=ParserError("Expected expression, found ',1]'"),
        ),
        Case(
            '[1, ["a"]]',
            expected_parse=AST.array([AST.int('1'), AST.array([AST.string('a')])]),
        ),

        # Tuples
        Case(
            '(1,)',
            expected_parse=AST.array([AST.int('1')]),
        ),
        Case(
            '(1)',
            expected_parse=ParserError("Expected /,/, found ')'"),
        ),
        Case(
            '(,)',
            expected_parse=ParserError("Expected expression, found ',)'"),
        ),
        Case(
            '(1,,)',
            expected_parse=ParserError("Expected expression, found ',)'"),
        ),
        Case(
            '(,1)',
            expected_parse=ParserError("Expected expression, found ',1)'"),
        ),
        Case(
            '(1, ("a",))',
            expected_parse=AST.array([AST.int('1'), AST.array([AST.string('a')])]),
        ),

        # Mappings
        Case(
            '{"a": 1}',
            expected_parse=AST.mapping({AST.string('a'): AST.int('1')}),
        ),
        Case(
            '{"a": 1,}',
            expected_parse=AST.mapping({AST.string('a'): AST.int('1')}),
        ),
        Case(
            '{"a": 1,,}',
            expected_parse=ParserError("Expected key, found ',}'"),
        ),
        Case(
            '{,"a": 1}',
            expected_parse=ParserError('Expected key, found \',"a": 1}\''),
        ),
        Case(
            '{a: 1}',
            expected_parse=AST.mapping({AST.identifier('a'): AST.int('1')}),
        ),

        # Sets
        Case(
            '{1}',
            expected_parse=AST.set([AST.int('1')]),
        ),
        Case(
            '{1,}',
            expected_parse=AST.set([AST.int('1')]),
        ),
        Case(
            '{1,,}',
            expected_parse=ParserError("Expected expression, found ',}'"),
        ),
        Case(
            '{,1}',
            expected_parse=ParserError("Expected key, found ',1}'"),
        ),
        Case(
            '{1, 2}',
            expected_parse=AST.set([AST.int('1'), AST.int('2')]),
        ),

        # Single-quoted strings
        Case(
            '''
                'text'
            ''',
            expected_parse=AST.string('text'),
        ),
        Case(
            r'''
                'I "love\" this'
            ''',
            expected_parse=AST.string('I "love" this'),
        ),
        Case(
            r'''
                'It\'s what\'s most'
            ''',
            expected_parse=AST.string("It's what's most"),
        ),
        Case(
            # NB input is raw string (i.e. the string includes the backslashes), output is not (so is parsed as normal Python
            # string literals are)
            r'''
                ' \\ \" \/ \b \f \n \r \t \u0424 \x7E \' '
            ''',
            expected_parse=AST.string(' \\ " / \x08 \x0C \n \r \t Ф ~ \' '),
        ),

        # Double-quoted strings
        Case(
            '''
                "text"
            ''',
            expected_parse=AST.string('text'),
        ),
        Case(
            r'''
                "I \"love\" this"
            ''',
            expected_parse=AST.string('I "love" this'),
        ),
        Case(
            r'''
                "It's what\'s most"
            ''',
            expected_parse=AST.string("It's what's most"),
        ),
        Case(
            # NB input is raw string (i.e. the string includes the backslashes), output is not (so is parsed as normal Python
            # string literals are)
            r'''
                " \\ \" \/ \b \f \n \r \t \u0424 \x7E \' "
            ''',
            expected_parse=AST.string(' \\ " / \x08 \x0C \n \r \t Ф ~ \' '),
        ),

        # Comments
        Case(
            '''
                36 // thirty-six
            ''',
            expected_parse=AST.int('36'),
        ),
        Case(
            '''
               // a comment
               "http://not.a.comment/"
            ''',
            expected_parse=AST.string('http://not.a.comment/'),
        ),

        # Python repr expressions
        Case(
            '<__main__.C object at 0x05b0ace99cf7>',
            expected_parse=AST.python_repr('<__main__.C object at 0x05b0ace99cf7>'),
        ),
        Case(
            "<re.Match object; span=(0, 1), match='a'>",
            expected_parse=AST.python_repr("<re.Match object; span=(0, 1), match='a'>"),
        ),
        Case(
            "<dummy match='<>'>",
            expected_parse=AST.python_repr("<dummy match='<>'>"),
        ),

        # Identifiers
        Case(
            'x',
            expected_parse=AST.identifier('x'),
        ),
        Case(
            'x10',
            expected_parse=AST.identifier('x10'),
        ),
        Case(
            'μεταφορά',
            expected_parse=AST.identifier('μεταφορά'),
        ),

        # Function calls
        Case(
            'x(1)',
            expected_parse=AST.function_call('x', [AST.int('1')]),
        ),
        Case(
            'x(1,)',
            expected_parse=AST.function_call('x', [AST.int('1')]),
        ),
        Case(
            'x(1, 2)',
            expected_parse=AST.function_call('x', [AST.int('1'), AST.int('2')]),
        ),

    ]
)
def test_parser(input_text, expected_parse):
    lexer = Lexer(input_text)
    mock_builder = AstClass()
    parser = Parser(lexer, mock_builder)
    try:
        document = parser.document()
        actual_parse, = document.values
    except ParserError as actual_error:
        if isinstance(expected_parse, ParserError):
            assert str(actual_error) == str(expected_parse)
        else:
            raise
    else:
        assert actual_parse == expected_parse
