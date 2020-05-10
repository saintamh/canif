#!/usr/bin/env python3

# standards
from io import StringIO
from typing import NamedTuple

# 3rd parties
import pytest

# canif
from canif.builder import PodsBuilder, PrettyPrintBuilder
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
    expected_pods: object = NotImplemented
    expected_json: str = NotImplemented


ALL_TEST_CASES = [

    # Numbers
    Case(
        '42',
        expected_parse=AST.int('42'),
        expected_pods=42,
        expected_json='42',
    ),
    Case(
        '3.14',
        expected_parse=AST.float('3.14'),
        expected_pods=3.14,
        expected_json='3.14',
    ),
    Case(
        '5.12e-1',
        expected_parse=AST.float('5.12e-1'),
        expected_pods=0.512,
        expected_json='0.512',
    ),
    Case(
        '5.12e-17',
        expected_parse=AST.float('5.12e-17'),
        expected_pods=5.12e-17,
        expected_json='5.12e-17',
    ),

    # Named constants
    Case(
        'true',
        expected_parse=AST.named_constant('true'),
        expected_pods=True,
        expected_json='true',
    ),
    Case(
        'false',
        expected_parse=AST.named_constant('false'),
        expected_pods=False,
        expected_json='false',
    ),
    Case(
        'True',
        expected_parse=AST.named_constant('True'),
        expected_pods=True,
        expected_json='true',
    ),
    Case(
        'False',
        expected_parse=AST.named_constant('False'),
        expected_pods=False,
        expected_json='false',
    ),
    Case(
        'null',
        expected_parse=AST.named_constant('null'),
        expected_pods=None,
        expected_json='null',
    ),
    Case(
        'None',
        expected_parse=AST.named_constant('None'),
        expected_pods=None,
        expected_json='null',
    ),
    Case(
        'undefined',
        expected_parse=AST.named_constant('undefined'),
        expected_pods='$undefined',
        expected_json='"$undefined"',
    ),
    Case(
        'NotImplemented',
        expected_parse=AST.named_constant('NotImplemented'),
        expected_pods=NotImplemented,
        expected_json='"$NotImplemented"',
    ),

    # Arrays
    Case(
        '[1]',
        expected_parse=AST.array([AST.int('1')]),
        expected_pods=[1],
        expected_json='[1]',
    ),
    Case(
        '[1,]',
        expected_parse=AST.array([AST.int('1')]),
        expected_pods=[1],
        expected_json='[1]',
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
        expected_pods=[1, ['a']],
        expected_json='[1, ["a"]]',
    ),

    # Tuples
    Case(
        '(1,)',
        expected_parse=AST.array([AST.int('1')]),
        expected_pods=[1],
        expected_json='[1]',
    ),
    Case(
        '(1)',
        expected_parse=ParserError("Expected /,/, found ')'"),
        expected_pods=[1],
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
        expected_pods=[1, ['a']],
        expected_json='[1, ["a"]]',
    ),

    # Mappings
    Case(
        '{}',
        expected_parse=AST.mapping({}),
        expected_pods={},
        expected_json='{}',
    ),
    Case(
        '{"a": 1}',
        expected_parse=AST.mapping({AST.string('a'): AST.int('1')}),
        expected_pods={'a': 1},
        expected_json='{"a": 1}',
    ),
    Case(
        '{"a": 1,}',
        expected_parse=AST.mapping({AST.string('a'): AST.int('1')}),
        expected_pods={'a': 1},
        expected_json='{"a": 1}',
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
        expected_parse=AST.mapping({AST.string('a'): AST.int('1')}),
        expected_pods={'a': 1},
        expected_json='{"a": 1}',
    ),

    # Sets
    Case(
        '{1}',
        expected_parse=AST.set([AST.int('1')]),
        expected_pods={1},
        expected_json='{"$set": [1]}',
    ),
    Case(
        '{1,}',
        expected_parse=AST.set([AST.int('1')]),
        expected_pods={1},
        expected_json='{"$set": [1]}',
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
        expected_pods={1, 2},
        expected_json='{"$set": [1, 2]}',
    ),

    # Single-quoted strings
    Case(
        '''
            'text'
        ''',
        expected_parse=AST.string('text'),
        expected_pods='text',
        expected_json='"text"',
    ),
    Case(
        r'''
            'I "love\" this'
        ''',
        expected_parse=AST.string('I "love" this'),
        expected_pods='I "love" this',
        expected_json=r'"I \"love\" this"',
    ),
    Case(
        r'''
            'It\'s Sam\'s hat'
        ''',
        expected_parse=AST.string("It's Sam's hat"),
        expected_pods="It's Sam's hat",
        expected_json='"It\'s Sam\'s hat"',
    ),
    Case(
        # NB input is raw string (i.e. the string includes the backslashes), output is not (so is parsed as normal Python
        # string literals are)
        r'''
            ' \\ \" \/ \b \f \n \r \t \u0424 \x7E \' '
        ''',
        expected_parse=AST.string(' \\ " / \x08 \x0C \n \r \t Ф ~ \' '),
        expected_pods=' \\ " / \x08 \x0C \n \r \t Ф ~ \' ',
        expected_json=r'''" \\ \" / \b \f \n \r \t Ф ~ ' "''',
    ),

    # Double-quoted strings
    Case(
        '''
            "text"
        ''',
        expected_parse=AST.string('text'),
        expected_pods='text',
        expected_json='"text"',
    ),
    Case(
        r'''
            "I \"love\" this"
        ''',
        expected_parse=AST.string('I "love" this'),
        expected_pods='I "love" this',
        expected_json=r'"I \"love\" this"',
    ),
    Case(
        r'''
            "It's Sam\'s hat"
        ''',
        expected_parse=AST.string("It's Sam's hat"),
        expected_pods="It's Sam's hat",
        expected_json='"It\'s Sam\'s hat"',
    ),
    Case(
        # NB input is raw string (i.e. the string includes the backslashes), output is not (so is parsed as normal Python
        # string literals are)
        r'''
            " \\ \" \/ \b \f \n \r \t \u0424 \x7E \' "
        ''',
        expected_parse=AST.string(' \\ " / \x08 \x0C \n \r \t Ф ~ \' '),
        expected_pods=' \\ " / \x08 \x0C \n \r \t Ф ~ \' ',
        expected_json=r'''" \\ \" / \b \f \n \r \t Ф ~ ' "''',
    ),

    # Comments
    Case(
        '''
            36 // thirty-six
        ''',
        expected_parse=AST.int('36'),
        expected_pods=36,
        expected_json='36',
    ),
    Case(
        '''
           // a comment
           "http://not.a.comment/"
        ''',
        expected_parse=AST.string('http://not.a.comment/'),
        expected_pods='http://not.a.comment/',
        expected_json='"http://not.a.comment/"',
    ),

    # Python repr expressions
    Case(
        '<__main__.C object at 0x05b0ace99cf7>',
        expected_parse=AST.python_repr('<__main__.C object at 0x05b0ace99cf7>'),
        expected_pods='$repr<__main__.C object at 0x05b0ace99cf7>',
        expected_json='"$repr<__main__.C object at 0x05b0ace99cf7>"',
    ),
    Case(
        "<re.Match object; span=(0, 1), match='a'>",
        expected_parse=AST.python_repr("<re.Match object; span=(0, 1), match='a'>"),
        expected_pods="$repr<re.Match object; span=(0, 1), match='a'>",
        expected_json='"$repr<re.Match object; span=(0, 1), match=\'a\'>"',
    ),
    Case(
        "<dummy match='<>'>",
        expected_parse=AST.python_repr("<dummy match='<>'>"),
        expected_pods="$repr<dummy match='<>'>",
        expected_json='"$repr<dummy match=\'<>\'>"',
    ),

    # Identifiers
    Case(
        'x',
        expected_parse=AST.identifier('x'),
        expected_pods='$$x',
        expected_json='"$$x"',
    ),
    Case(
        'x10',
        expected_parse=AST.identifier('x10'),
        expected_pods='$$x10',
        expected_json='"$$x10"',
    ),
    Case(
        'μεταφορά',
        expected_parse=AST.identifier('μεταφορά'),
        expected_pods='$$μεταφορά',
        expected_json='"$$μεταφορά"',
    ),

    # Function calls
    Case(
        'x(1)',
        expected_parse=AST.function_call('x', [AST.int('1')]),
        expected_pods={'$$x': [1]},
        expected_json='{"$$x": [1]}',
    ),
    Case(
        'x(1,)',
        expected_parse=AST.function_call('x', [AST.int('1')]),
        expected_pods={'$$x': [1]},
        expected_json='{"$$x": [1]}',
    ),
    Case(
        'x(1, 2)',
        expected_parse=AST.function_call('x', [AST.int('1'), AST.int('2')]),
        expected_pods={'$$x': [1, 2]},
        expected_json='{"$$x": [1, 2]}',
    ),

    # Known function calls
    Case(
        'OrderedDict([("a", 1), ("b", 2)])',
        expected_parse=AST.function_call(
            'OrderedDict',
            [
                AST.array([
                    AST.array([AST.string('a'), AST.int('1')]),
                    AST.array([AST.string('b'), AST.int('2')]),
                ]),
            ],
        ),
        expected_pods={'a': 1, 'b': 2},
        expected_json='{"a": 1, "b": 2}',
    ),
    Case(
        # MongoDB BSON date objects
        'Date("1970-09-12")',
        expected_parse=AST.function_call('Date', [AST.string('1970-09-12')]),
        expected_pods={'$date': '1970-09-12'},
        expected_json='{"$date": "1970-09-12"}',
    ),
    Case(
        # MongoDB BSON ObjectId objects
        'ObjectId("1234")',
        expected_parse=AST.function_call('ObjectId', [AST.string('1234')]),
        expected_pods={'$oid': '1234'},
        expected_json='{"$oid": "1234"}',
    ),
]


@pytest.mark.parametrize(','.join(Case._fields), ALL_TEST_CASES)
def test_parser(input_text, expected_parse, expected_pods, expected_json):
    del expected_pods, expected_json  # not used in this test, pylint
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


@pytest.mark.parametrize(','.join(Case._fields), ALL_TEST_CASES)
def test_pods(input_text, expected_parse, expected_pods, expected_json):
    del expected_json  # not used in this test, pylint
    lexer = Lexer(input_text)
    builder = PodsBuilder()
    parser = Parser(lexer, builder)
    try:
        actual_pods = parser.document()
    except ParserError as actual_error:
        if isinstance(expected_parse, ParserError):
            assert str(actual_error) == str(expected_parse)
        else:
            raise
    else:
        assert not isinstance(expected_parse, ParserError)
        assert actual_pods == expected_pods


@pytest.mark.parametrize(','.join(Case._fields), ALL_TEST_CASES)
def test_json_output(input_text, expected_parse, expected_pods, expected_json):
    del expected_pods  # not used in this test, pylint
    output_buffer = StringIO()
    lexer = Lexer(input_text)
    builder = PrettyPrintBuilder(output_buffer, flatten=True)
    parser = Parser(lexer, builder)
    try:
        parser.document()
        actual_json = output_buffer.getvalue()
    except ParserError as actual_error:
        if isinstance(expected_parse, ParserError):
            assert str(actual_error) == str(expected_parse)
        else:
            raise
    else:
        assert not isinstance(expected_json, ParserError)
        assert actual_json == expected_json
