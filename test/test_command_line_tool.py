#!/usr/bin/env python3

# standards
from glob import glob
from os import path
import re
import shlex
from subprocess import PIPE, check_output, run
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
        input=test.input_text,
        encoding='UTF-8',
    )
    try:
        assert actual_output_text == test.expected_output_text
    except AssertionError:
        print(test.input_text)
        print(actual_output_text)
        raise


def iter_positions_for_spanner():
    # The 'fingerprint' mechanism is to limit the number of places where we throw in the spanner, else if we insert it at every
    # possible position we end up with 4000+ tests, which take ages to run
    seen_fingerprints = set()
    radius = 2
    for test in iter_test_cases():
        works = re.sub(r'(?<=//).*', lambda m: '\0' * len(m.group()), test.input_text)
        works = re.sub(r'\w', 'x', re.sub(r'\s', ' ', works))
        works = '\0' * radius + works + '\0' * radius
        for position in range(len(test.input_text) + 1):
            fingerprint = works[position : position + 2*radius]
            if fingerprint not in seen_fingerprints and '\0' not in works[position+1 : position+3]:
                seen_fingerprints.add(fingerprint)
                yield test, position


@pytest.mark.parametrize(
    'test, position',
    iter_positions_for_spanner()
)
def test_recovery(test, position):
    """
    The program prints the formatted output incrementally as it parses the input. This means that if we encounter a syntax error
    while parsing, we've already printed out part of the output. We want to then print the unparsed input, such that the output
    will be formatted up to the syntax error, and then a raw echo of the rest of the input.
    """
    spanner = '<"\'>'
    works = test.input_text
    assert spanner not in works  # else the logic below doesn't hold

    # Throw the spanner in the works. The command should then fail, and its stdout will be half formatted, half not
    input_text = works[:position] + spanner + works[position:]
    print('-- input_text --')
    print(input_text)
    result = run(
        test.argv + ['--single-document'],
        input=input_text,
        stdout=PIPE,
        stderr=PIPE,
        encoding='UTF-8',
        check=False,
    )
    try:
        assert result.returncode > 0, result.returncode  # it should've failed
    except AssertionError:
        print(input_text)
        raise

    half_formatted_text = result.stdout
    print('-- half_formatted_text --')
    print(half_formatted_text)

    # We then take the half-formatted output, remove the spanner, and feed that back to the program. Then we should get the
    # expected output, meaning the half-formatted text was still equivalent to the input (just ill-formatted)
    fixed_input_text = half_formatted_text.replace(spanner, '')
    fixed_output_text = check_output(
        test.argv,
        input=fixed_input_text,
        encoding='UTF-8',
    )
    print('-- fixed_output_text --')
    print(fixed_output_text)

    try:
        assert fixed_output_text == test.expected_output_text
    except AssertionError:
        print(fixed_input_text)
        print('-- ')
        print(fixed_output_text)
        raise
