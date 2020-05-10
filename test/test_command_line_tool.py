#!/usr/bin/env python3

# standards
from glob import glob
from os import path
import shlex
from subprocess import check_output

# 3rd parties
import pytest


@pytest.mark.parametrize(
    'input_file_path', glob(path.join(path.dirname(__file__), 'fixtures', '*.in'))
)
def test_command_line_tool(input_file_path):
    output_file_path = input_file_path.replace('.in', '.out')
    argv_file_path = input_file_path.replace('.in', '.argv')

    with open(output_file_path, 'rb') as file_in:
        expected_output_bytes = file_in.read()
    if path.exists(argv_file_path):
        with open(argv_file_path, 'rt', encoding='UTF-8') as file_in:
            argv = shlex.split(file_in.read().strip())
    else:
        argv = ['canif']

    with open(input_file_path, 'rb') as file_in:
        actual_output_bytes = check_output(
            argv,
            stdin=file_in,
        )

    assert actual_output_bytes == expected_output_bytes
