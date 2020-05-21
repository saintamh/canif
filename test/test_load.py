#!/usr/bin/env python3

# standards
from io import StringIO

# 3rd parties
import pytest

# canif
import canif


def test_loads():
    assert canif.loads('{"a": 1}') == {'a': 1}


def test_loads_parser_error():
    with pytest.raises(canif.ParserError) as error:
        canif.loads('{a": 1}')
    assert str(error.value) == 'Position 2: expected `:`, found \'": 1}\''


def test_load():
    assert canif.load(StringIO('{"a": 1}')) == {'a': 1}


def test_load_parser_error():
    with pytest.raises(canif.ParserError) as error:
        canif.load(StringIO('{a": 1}'))
    assert str(error.value) == 'Position 2: expected `:`, found \'": 1}\''
