#!/usr/bin/env python3

# standards
from glob import glob
from os import path
import shlex
from subprocess import check_output
from typing import List, NamedTuple

# 3rd parties
import pytest


class Case(NamedTuple):
    file_name: str
    argv: List[str]
    input_text: bytes
    expected_output_text: bytes

    def __repr__(self):
        # So that the test IDs are more sensible
        return '%s < %s' % (self.argv, self.file_name)


def iter_test_cases():
    for input_file_path in glob(path.join(path.dirname(__file__), 'fixtures', '*')):
        file_name = path.basename(input_file_path)
        with open(input_file_path, 'rt', encoding='UTF-8') as file_in:
            input_text, *all_output_sections = file_in.read().split('\n--\n$ canif')
        assert all_output_sections, input_file_path
        for section in all_output_sections:
            argv, expected_output_text = section.split('\n', 1)
            argv = ['canif', *shlex.split(argv)]
            yield Case(
                file_name,
                argv,
                input_text,
                expected_output_text,
            )


@pytest.mark.parametrize('test', iter_test_cases())
def test_command_line_tool(test):
    actual_output_text = check_output(
        test.argv,
        input=test.input_text.encode('UTF-8'),
    ).decode('UTF-8')
    try:
        assert actual_output_text == test.expected_output_text
    except AssertionError:
        print(actual_output_text)
        raise
