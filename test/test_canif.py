#!/usr/bin/env python3

# standards
from glob import glob
from os import path
import shlex

# 3rd parties
import pytest

# canif
import canif


@pytest.mark.parametrize(
    'input_file_path', glob(path.join(path.dirname(__file__), 'fixtures', '*.in'))
)
def test_canif(input_file_path):
    output_file_path = input_file_path.replace('.in', '.out')
    argv_file_path = input_file_path.replace('.in', '.argv')

    with open(input_file_path, 'rb') as file_in:
        input_bytes = file_in.read()
    with open(output_file_path, 'rb') as file_in:
        expected_output_bytes = file_in.read()
    if path.exists(argv_file_path):
        with open(argv_file_path, 'rt', encoding='UTF-8') as file_in:
            argv = shlex.split(file_in.read().strip())
    else:
        argv = ['canif']

    options = canif.parse_command_line(
        argv,
        default_input_encoding='UTF-8',
        default_output_encoding='UTF-8',
    )
    exit_status, actual_output_bytes = canif.run(options, input_bytes)

    assert exit_status == 0
    assert actual_output_bytes == expected_output_bytes
