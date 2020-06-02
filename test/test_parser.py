#!/usr/bin/env python3

# standards
from io import StringIO
from typing import NamedTuple

# 3rd parties
import pytest

# canif
from canif.builder import JsonPrinter, PodsBuilder, VerbatimPrinter
from canif.lexer import Lexer
from canif.parser import Parser, ParserError
from canif.utils import undefined


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

    def __init__(self):
        self.parse = NotImplemented

    def __getattr__(self, node_kind):
        def callback(*values):
            node = AstNode(node_kind, values)
            if self.parse is not NotImplemented:
                self.parse.append(node)
            return node
        return callback

    def open_document(self):
        assert self.parse is NotImplemented
        self.parse = []

    def close_document(self):
        parse = self.parse
        self.parse = NotImplemented
        return parse


AST = AstClass()


class Case(NamedTuple):
    input_text: str
    expected_parse: AstNode
    expected_pods: object = NotImplemented
    expected_verb: str = NotImplemented
    expected_json: str = NotImplemented


ALL_TEST_CASES = [

    # Numbers
    Case(
        '42',
        expected_parse=[AST.int('42', 42)],
        expected_pods=42,
        expected_verb='42',
        expected_json='42',
    ),
    Case(
        '3.14',
        expected_parse=[AST.float('3.14', 3.14)],
        expected_pods=3.14,
        expected_verb='3.14',
        expected_json='3.14',
    ),
    Case(
        '5.12e-1',
        expected_parse=[AST.float('5.12e-1', 5.12e-1)],
        expected_pods=0.512,
        expected_verb='5.12e-1',
        expected_json='0.512',
    ),
    Case(
        '5.12e-17',
        expected_parse=[AST.float('5.12e-17', 5.12e-17)],
        expected_pods=5.12e-17,
        expected_verb='5.12e-17',
        expected_json='5.12e-17',
    ),

    # Named constants
    Case(
        'true',
        expected_parse=[AST.bool('true', True)],
        expected_pods=True,
        expected_verb='true',
        expected_json='true',
    ),
    Case(
        'false',
        expected_parse=[AST.bool('false', False)],
        expected_pods=False,
        expected_verb='false',
        expected_json='false',
    ),
    Case(
        'True',
        expected_parse=[AST.bool('True', True)],
        expected_pods=True,
        expected_verb='True',
        expected_json='true',
    ),
    Case(
        'False',
        expected_parse=[AST.bool('False', False)],
        expected_pods=False,
        expected_verb='False',
        expected_json='false',
    ),
    Case(
        'null',
        expected_parse=[AST.null('null')],
        expected_pods=None,
        expected_verb='null',
        expected_json='null',
    ),
    Case(
        'None',
        expected_parse=[AST.null('None')],
        expected_pods=None,
        expected_verb='None',
        expected_json='null',
    ),
    Case(
        'undefined',
        expected_parse=[AST.named_constant('undefined', undefined)],
        expected_pods=undefined,
        expected_verb='undefined',
        expected_json='"$undefined"',
    ),
    Case(
        'NotImplemented',
        expected_parse=[AST.named_constant('NotImplemented', NotImplemented)],
        expected_pods=NotImplemented,
        expected_verb='NotImplemented',
        expected_json='"$NotImplemented"',
    ),

    # Arrays
    Case(
        '[]',
        expected_parse=[
            AST.open_array(list),
            AST.close_array(),
        ],
        expected_pods=[],
        expected_verb='[]',
        expected_json='[]',
    ),
    Case(
        '[1]',
        expected_parse=[
            AST.open_array(list),
            AST.int('1', 1),
            AST.array_element(),
            AST.close_array(),
        ],
        expected_pods=[1],
        expected_verb='[1]',
        expected_json='[1]',
    ),
    Case(
        '[1, ["a"]]',
        expected_parse=[
            AST.open_array(list),
            AST.int('1', 1),
            AST.array_element(),
            AST.open_array(list),
            AST.string('"a"', 'a'),
            AST.array_element(),
            AST.close_array(),
            AST.array_element(),
            AST.close_array(),
        ],
        expected_pods=[1, ['a']],
        expected_verb='[1, ["a"]]',
        expected_json='[1, ["a"]]',
    ),

    # Empty array slots (square bracket arrays only)
    Case(
        '[1,2,,,]',
        expected_parse=[
            AST.open_array(list),
            AST.int('1', 1),
            AST.array_element(),
            AST.int('2', 2),
            AST.array_element(),
            AST.array_empty_slot(),
            AST.array_element(),
            AST.array_empty_slot(),
            AST.array_element(),
            AST.close_array(),
        ],
        expected_pods=[1, 2, None, None],
        expected_verb='[1, 2, , ,]',
        expected_json='[1, 2, null, null]',
    ),
    Case(
        '[1,,,4]',
        expected_parse=[
            AST.open_array(list),
            AST.int('1', 1),
            AST.array_element(),
            AST.array_empty_slot(),
            AST.array_element(),
            AST.array_empty_slot(),
            AST.array_element(),
            AST.int('4', 4),
            AST.array_element(),
            AST.close_array(),
        ],
        expected_pods=[1, None, None, 4],
        expected_verb='[1, , , 4]',
        expected_json='[1, null, null, 4]',
    ),
    Case(
        '[,,3,4]',
        expected_parse=[
            AST.open_array(list),
            AST.array_empty_slot(),
            AST.array_element(),
            AST.array_empty_slot(),
            AST.array_element(),
            AST.int('3', 3),
            AST.array_element(),
            AST.int('4', 4),
            AST.array_element(),
            AST.close_array(),
        ],
        expected_pods=[None, None, 3, 4],
        expected_verb='[, , 3, 4]',
        expected_json='[null, null, 3, 4]',
    ),
    Case(
        '[,,3,4,]',
        expected_parse=[
            AST.open_array(list),
            AST.array_empty_slot(),
            AST.array_element(),
            AST.array_empty_slot(),
            AST.array_element(),
            AST.int('3', 3),
            AST.array_element(),
            AST.int('4', 4),
            AST.array_element(),
            AST.close_array(),
        ],
        expected_pods=[None, None, 3, 4],
        expected_verb='[, , 3, 4]',
        expected_json='[null, null, 3, 4]',
    ),

    # Tuples
    Case(
        '()',
        expected_parse=[
            AST.open_array(tuple),
            AST.close_array(),
        ],
        expected_pods=(),
        expected_verb='()',
        expected_json='[]',
    ),
    Case(
        '(1,)',
        expected_parse=[
            AST.open_array(tuple),
            AST.int('1', 1),
            AST.array_element(),
            AST.close_array(),
        ],
        expected_pods=(1,),
        expected_verb='(1,)',
        expected_json='[1]',
    ),
    Case(
        '(1)',
        expected_parse=ParserError("Position 2: expected `,`, found ')'"),
    ),
    Case(
        '(,)',
        expected_parse=ParserError("Position 1: expected expression, found ',)'"),
    ),
    Case(
        '(1,,)',
        expected_parse=ParserError("Position 3: expected expression, found ',)'"),
    ),
    Case(
        '(,1)',
        expected_parse=ParserError("Position 1: expected expression, found ',1)'"),
    ),
    Case(
        '(1, ("a",))',
        expected_parse=[
            AST.open_array(tuple),
            AST.int('1', 1),
            AST.array_element(),
            AST.open_array(tuple),
            AST.string('"a"', 'a'),
            AST.array_element(),
            AST.close_array(),
            AST.array_element(),
            AST.close_array(),
        ],
        expected_pods=(1, ('a',)),
        expected_verb='(1, ("a",))',
        expected_json='[1, ["a"]]',
    ),

    # Mappings
    Case(
        '{}',
        expected_parse=[
            AST.open_mapping(),
            AST.close_mapping(),
        ],
        expected_pods={},
        expected_verb='{}',
        expected_json='{}',
    ),
    Case(
        '{"a": 1}',
        expected_parse=[
            AST.open_mapping(),
            AST.string('"a"', 'a'),
            AST.mapping_key(),
            AST.int('1', 1),
            AST.mapping_value(),
            AST.close_mapping(),
        ],
        expected_pods={'a': 1},
        expected_verb='{"a": 1}',
        expected_json='{"a": 1}',
    ),
    Case(
        '{"a": 1,}',
        expected_parse=[
            AST.open_mapping(),
            AST.string('"a"', 'a'),
            AST.mapping_key(),
            AST.int('1', 1),
            AST.mapping_value(),
            AST.close_mapping(),
        ],
        expected_pods={'a': 1},
        expected_verb='{"a": 1}',
        expected_json='{"a": 1}',
    ),
    Case(
        '{"a": 1,,}',
        expected_parse=ParserError("Position 8: expected key, found ',}'"),
    ),
    Case(
        '{,"a": 1}',
        expected_parse=ParserError('Position 1: expected key, found \',"a": 1}\''),
    ),
    Case(
        '{a: a}',
        expected_parse=[
            AST.open_mapping(),
            AST.string('a', 'a'),
            AST.mapping_key(),
            AST.identifier('a'),
            AST.mapping_value(),
            AST.close_mapping(),
        ],
        expected_pods={'a': '$$a'},
        expected_verb='{a: a}',
        expected_json='{"a": "$$a"}',
    ),

    # # Mappings with tuples as keys
    # Case(
    #     '{(1, 2): 3}',
    #     expected_parse=[
    #         AST.open_mapping(),
    #         AST.open_array(tuple),
    #         AST.int('1', 1),
    #         AST.array_element(),
    #         AST.int('2', 2),
    #         AST.array_element(),
    #         AST.close_array(),
    #         AST.mapping_key(),
    #         AST.int('3', 3),
    #         AST.mapping_value(),
    #         AST.close_mapping(),
    #     ],
    #     expected_pods={(1, 2): 3},
    #     expected_verb='{(1, 2): 3}',
    #     expected_json='{"$tuple[1, 2]": 3}',
    # ),
    # Case(
    #     '{(1, (2, "3")): 4}',
    #     expected_parse=[
    #         AST.open_mapping(),
    #         AST.open_array(tuple),
    #         AST.int('1', 1),
    #         AST.array_element(),
    #         AST.open_array(tuple),
    #         AST.int('2', 2),
    #         AST.array_element(),
    #         AST.string('"3"', '3'),
    #         AST.array_element(),
    #         AST.close_array(),
    #         AST.array_element(),
    #         AST.close_array(),
    #         AST.mapping_key(),
    #         AST.int('4', 4),
    #         AST.mapping_value(),
    #         AST.close_mapping(),
    #     ],
    #     expected_pods={(1, (2, '3')): 4},
    #     expected_verb=r'{(1, (2, "3")): 4}',
    #     expected_json=r'{"$tuple[1, [2, \"3\"]]": 4}',
    # ),

    # Sets
    Case(
        '{1}',
        expected_parse=[
            AST.open_set(),
            AST.int('1', 1),
            AST.set_element(),
            AST.close_set(),
        ],
        expected_pods={1},
        expected_verb='{1}',
        expected_json='{"$set": [1]}',
    ),
    Case(
        '{1,}',
        expected_parse=[
            AST.open_set(),
            AST.int('1', 1),
            AST.set_element(),
            AST.close_set(),
        ],
        expected_pods={1},
        expected_verb='{1}',
        expected_json='{"$set": [1]}',
    ),
    Case(
        '{1,,}',
        expected_parse=ParserError("Position 3: expected expression, found ',}'"),
    ),
    Case(
        '{,1}',
        expected_parse=ParserError("Position 1: expected key, found ',1}'"),
    ),
    Case(
        '{1, 2}',
        expected_parse=[
            AST.open_set(),
            AST.int('1', 1),
            AST.set_element(),
            AST.int('2', 2),
            AST.set_element(),
            AST.close_set(),
        ],
        expected_pods={1, 2},
        expected_verb='{1, 2}',
        expected_json='{"$set": [1, 2]}',
    ),
    Case(
        '{a, b}',
        expected_parse=[
            AST.open_set(),
            AST.identifier('a'),
            AST.set_element(),
            AST.identifier('b'),
            AST.set_element(),
            AST.close_set(),
        ],
        expected_pods={'$$a', '$$b'},
        expected_verb='{a, b}',
        expected_json='{"$set": ["$$a", "$$b"]}',
    ),

    # Single-quoted strings
    Case(
        '''
            'text'
        ''',
        expected_parse=[AST.string("'text'", 'text')],
        expected_pods='text',
        expected_verb="'text'",
        expected_json='"text"',
    ),
    Case(
        r'''
            'I "love\" this'
        ''',
        expected_parse=[AST.string(r"""'I "love\" this'""", 'I "love" this')],  # pylint: disable=invalid-triple-quote
        expected_pods='I "love" this',
        expected_verb=r"""'I "love\" this'""",  # pylint: disable=invalid-triple-quote
        expected_json=r'"I \"love\" this"',
    ),
    Case(
        r'''
            'It\'s Sam\'s hat'
        ''',
        expected_parse=[AST.string(r"""'It\'s Sam\'s hat'""", "It's Sam's hat")],  # pylint: disable=invalid-triple-quote
        expected_pods="It's Sam's hat",
        expected_verb=r"'It\'s Sam\'s hat'",
        expected_json='"It\'s Sam\'s hat"',
    ),
    Case(
        # NB input is raw string (i.e. the string includes the backslashes), output is not (so is parsed as normal Python
        # string literals are)
        r'''
            ' \\ \" \/ \b \f \n \r \t \u0424 \x7E \' '
        ''',
        expected_parse=[
            AST.string(
                r"""' \\ \" \/ \b \f \n \r \t \u0424 \x7E \' '""",  # pylint: disable=invalid-triple-quote
                ' \\ " / \x08 \x0C \n \r \t Ф ~ \' ',
            ),
        ],
        expected_pods=' \\ " / \x08 \x0C \n \r \t Ф ~ \' ',
        expected_verb=r"""' \\ \" \/ \b \f \n \r \t \u0424 \x7E \' '""",  # pylint: disable=invalid-triple-quote
        expected_json=r'''" \\ \" / \b \f \n \r \t Ф ~ ' "''',
    ),

    # Double-quoted strings
    Case(
        '''
            "text"
        ''',
        expected_parse=[AST.string('"text"', 'text')],
        expected_pods='text',
        expected_verb='"text"',
        expected_json='"text"',
    ),
    Case(
        r'''
            "I \"love\" this"
        ''',
        expected_parse=[AST.string(r'''"I \"love\" this"''', 'I "love" this')],
        expected_pods='I "love" this',
        expected_verb=r'"I \"love\" this"',
        expected_json=r'"I \"love\" this"',
    ),
    Case(
        r'''
            "It's Sam\'s hat"
        ''',
        expected_parse=[AST.string(r'''"It's Sam\'s hat"''', "It's Sam's hat")],
        expected_pods="It's Sam's hat",
        expected_verb=r'''"It's Sam\'s hat"''',
        expected_json='"It\'s Sam\'s hat"',
    ),
    Case(
        # NB input is raw string (i.e. the string includes the backslashes), output is not (so is parsed as normal Python
        # string literals are)
        r'''
            " \\ \" \/ \b \f \n \r \t \u0424 \x7E \' "
        ''',
        expected_parse=[
            AST.string(
                r'''" \\ \" \/ \b \f \n \r \t \u0424 \x7E \' "''',
                ' \\ " / \x08 \x0C \n \r \t Ф ~ \' ',
            ),
        ],
        expected_pods=' \\ " / \x08 \x0C \n \r \t Ф ~ \' ',
        expected_verb=r'''" \\ \" \/ \b \f \n \r \t \u0424 \x7E \' "''',
        expected_json=r'''" \\ \" / \b \f \n \r \t Ф ~ ' "''',
    ),

    # Comments
    Case(
        '''
            36 // thirty-six
        ''',
        expected_parse=[AST.int('36', 36)],
        expected_pods=36,
        expected_verb='36',
        expected_json='36',
    ),
    Case(
        '''
           // a comment
           "http://not.a.comment/"
        ''',
        expected_parse=[AST.string('"http://not.a.comment/"', 'http://not.a.comment/')],
        expected_pods='http://not.a.comment/',
        expected_verb='"http://not.a.comment/"',
        expected_json='"http://not.a.comment/"',
    ),

    # Python repr expressions
    Case(
        '<__main__.C object at 0x05b0ace99cf7>',
        expected_parse=[AST.python_repr('<__main__.C object at 0x05b0ace99cf7>')],
        expected_pods='$repr<__main__.C object at 0x05b0ace99cf7>',
        expected_verb='<__main__.C object at 0x05b0ace99cf7>',
        expected_json='"$repr<__main__.C object at 0x05b0ace99cf7>"',
    ),
    Case(
        "<re.Match object; span=(0, 1), match='a'>",
        expected_parse=[AST.python_repr("<re.Match object; span=(0, 1), match='a'>")],
        expected_pods="$repr<re.Match object; span=(0, 1), match='a'>",
        expected_verb="<re.Match object; span=(0, 1), match='a'>",
        expected_json='"$repr<re.Match object; span=(0, 1), match=\'a\'>"',
    ),
    Case(
        "<dummy match='<>'>",
        expected_parse=[AST.python_repr("<dummy match='<>'>")],
        expected_pods="$repr<dummy match='<>'>",
        expected_verb="<dummy match='<>'>",
        expected_json='"$repr<dummy match=\'<>\'>"',
    ),

    # Identifiers
    Case(
        'x',
        expected_parse=[AST.identifier('x')],
        expected_pods='$$x',
        expected_verb='x',
        expected_json='"$$x"',
    ),
    Case(
        'x10',
        expected_parse=[AST.identifier('x10')],
        expected_pods='$$x10',
        expected_verb='x10',
        expected_json='"$$x10"',
    ),
    Case(
        'μεταφορά',
        expected_parse=[AST.identifier('μεταφορά')],
        expected_pods='$$μεταφορά',
        expected_verb='μεταφορά',
        expected_json='"$$μεταφορά"',
    ),

    # Function calls
    Case(
        'x(1)',
        expected_parse=[
            AST.open_function_call('x'),
            AST.int('1', 1),
            AST.function_call_positional_argument(),
            AST.function_call_end_positional_arguments(),
            AST.close_function_call(),
        ],
        expected_pods={'$$x': [1]},
        expected_verb='x(1)',
        expected_json='{"$$x": [1]}',
    ),
    Case(
        'x(1,)',
        expected_parse=[
            AST.open_function_call('x'),
            AST.int('1', 1),
            AST.function_call_positional_argument(),
            AST.function_call_end_positional_arguments(),
            AST.close_function_call(),
        ],
        expected_pods={'$$x': [1]},
        expected_verb='x(1)',
        expected_json='{"$$x": [1]}',
    ),
    Case(
        'x(1, 2)',
        expected_parse=[
            AST.open_function_call('x'),
            AST.int('1', 1),
            AST.function_call_positional_argument(),
            AST.int('2', 2),
            AST.function_call_positional_argument(),
            AST.function_call_end_positional_arguments(),
            AST.close_function_call(),
        ],
        expected_pods={'$$x': [1, 2]},
        expected_verb='x(1, 2)',
        expected_json='{"$$x": [1, 2]}',
    ),

    # Function calls with kwargs
    Case(
        'x(a=1)',
        expected_parse=[
            AST.open_function_call('x'),
            AST.function_call_end_positional_arguments(),
            AST.function_call_start_keyword_arguments(),
            AST.string('a', 'a'),
            AST.function_call_keyword_argument_key(),
            AST.int('1', 1),
            AST.function_call_keyword_argument_value(),
            AST.function_call_end_keyword_arguments(),
            AST.close_function_call(),
        ],
        expected_pods={'$$x': [], '$kwargs': {'a': 1}},
        expected_verb='x(a=1)',
        expected_json='{"$$x": [], "$kwargs": {"a": 1}}',
    ),
    Case(
        'x(a=1,)',
        expected_parse=[
            AST.open_function_call('x'),
            AST.function_call_end_positional_arguments(),
            AST.function_call_start_keyword_arguments(),
            AST.string('a', 'a'),
            AST.function_call_keyword_argument_key(),
            AST.int('1', 1),
            AST.function_call_keyword_argument_value(),
            AST.function_call_end_keyword_arguments(),
            AST.close_function_call(),
        ],
        expected_pods={'$$x': [], '$kwargs': {'a': 1}},
        expected_verb='x(a=1)',
        expected_json='{"$$x": [], "$kwargs": {"a": 1}}',
    ),
    Case(
        'x(a=1, 2)',
        expected_parse=ParserError('Position 7: positional argument follows keyword argument'),
    ),
    Case(
        'x(a=1, b)',
        expected_parse=ParserError('Position 8: positional argument follows keyword argument'),
    ),
    Case(
        'x(a=1,,)',
        expected_parse=ParserError('Position 6: positional argument follows keyword argument'),
    ),
    Case(
        'x(a=1, b=2)',
        expected_parse=[
            AST.open_function_call('x'),
            AST.function_call_end_positional_arguments(),
            AST.function_call_start_keyword_arguments(),
            AST.string('a', 'a'),
            AST.function_call_keyword_argument_key(),
            AST.int('1', 1),
            AST.function_call_keyword_argument_value(),
            AST.string('b', 'b'),
            AST.function_call_keyword_argument_key(),
            AST.int('2', 2),
            AST.function_call_keyword_argument_value(),
            AST.function_call_end_keyword_arguments(),
            AST.close_function_call(),
        ],
        expected_pods={'$$x': [], '$kwargs': {'a': 1, 'b': 2}},
        expected_verb='x(a=1, b=2)',
        expected_json='{"$$x": [], "$kwargs": {"a": 1, "b": 2}}',
    ),

    # Known function calls
    Case(
        # MongoDB BSON date objects
        'Date("1970-09-12")',
        expected_parse=[
            AST.open_function_call('Date'),
            AST.string('"1970-09-12"', '1970-09-12'),
            AST.function_call_positional_argument(),
            AST.function_call_end_positional_arguments(),
            AST.close_function_call(),
        ],
        expected_pods={'$date': ['1970-09-12']},
        expected_verb='Date("1970-09-12")',
        expected_json='{"$date": ["1970-09-12"]}',
    ),
    Case(
        # MongoDB BSON ObjectId objects
        'ObjectId("1234")',
        expected_parse=[
            AST.open_function_call('ObjectId'),
            AST.string('"1234"', '1234'),
            AST.function_call_positional_argument(),
            AST.function_call_end_positional_arguments(),
            AST.close_function_call(),
        ],
        expected_pods={'$oid': ['1234']},
        expected_verb='ObjectId("1234")',
        expected_json='{"$oid": ["1234"]}',
    ),
]


@pytest.mark.parametrize(','.join(Case._fields), ALL_TEST_CASES)
def test_parser(input_text, expected_parse, expected_pods, expected_verb, expected_json):
    del expected_pods, expected_verb, expected_json  # not used in this test, pylint
    lexer = Lexer(input_text)
    mock_builder = AstClass()
    parser = Parser(lexer, mock_builder)
    try:
        actual_parse = parser.document()
    except ParserError as actual_error:
        if isinstance(expected_parse, ParserError):
            assert str(actual_error) == str(expected_parse)
        else:
            raise
    else:
        assert actual_parse == expected_parse


@pytest.mark.parametrize(','.join(Case._fields), ALL_TEST_CASES)
def test_pods(input_text, expected_parse, expected_pods, expected_verb, expected_json):
    del expected_json, expected_verb  # not used in this test, pylint
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
def test_verb(input_text, expected_parse, expected_pods, expected_verb, expected_json):
    del expected_pods, expected_json  # not used in this test, pylint
    output_buffer = StringIO()
    lexer = Lexer(input_text)
    builder = VerbatimPrinter(output_buffer, indent=0)
    parser = Parser(lexer, builder)
    try:
        parser.document()
        actual_verb = output_buffer.getvalue().rstrip()
    except ParserError as actual_error:
        if isinstance(expected_parse, ParserError):
            assert str(actual_error) == str(expected_parse)
        else:
            raise
    else:
        assert not isinstance(expected_verb, ParserError)
        assert actual_verb == expected_verb


@pytest.mark.parametrize(','.join(Case._fields), ALL_TEST_CASES)
def test_json_output(input_text, expected_parse, expected_pods, expected_verb, expected_json):
    del expected_pods, expected_verb  # not used in this test, pylint
    output_buffer = StringIO()
    lexer = Lexer(input_text)
    builder = JsonPrinter(output_buffer, indent=0)
    parser = Parser(lexer, builder)
    try:
        parser.document()
        actual_json = output_buffer.getvalue().rstrip()
    except ParserError as actual_error:
        if isinstance(expected_parse, ParserError):
            assert str(actual_error) == str(expected_parse)
        else:
            raise
    else:
        assert not isinstance(expected_json, ParserError)
        assert actual_json == expected_json
