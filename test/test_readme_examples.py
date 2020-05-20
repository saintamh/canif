#!/usr/bin/env python3

# standards
from doctest import DocTestParser, DocTestRunner
from os import chdir, path
import re
from subprocess import check_output
from tempfile import TemporaryDirectory

# canif
import canif


def test_readme_examples():
    readme_file_path = path.join(path.dirname(__file__), '..', 'README.md')
    with open(readme_file_path, 'rt', encoding='UTF-8') as file_in:
        all_blocks = re.findall(r'```(\w+)\s+(.+?)```', file_in.read(), flags=re.S)
    with TemporaryDirectory() as temp_dir:
        chdir(temp_dir)
        for syntax, block in all_blocks:
            if syntax == 'console':
                command_match = re.search(r'^\$ (\w+) (.+)\s+', block)
                if not command_match:
                    raise ValueError(block)
                print(command_match.group().rstrip())
                command, args = command_match.groups()
                block = block[command_match.end():]

                if command == 'cat':
                    # save the sample file to an actual file
                    file_name = args
                    with open(path.join(temp_dir, file_name), 'wt', encoding='UTF-8') as file_out:
                        file_out.write(block)

                else:
                    # check that the command output is as expcted
                    actual_output = check_output(
                        '%s %s' % (command, args),
                        shell=True,
                        cwd=temp_dir,
                        encoding='UTF-8',
                    )
                    assert actual_output == block

            elif syntax == 'pycon':
                parser = DocTestParser()
                test = parser.get_doctest(block, {'canif': canif}, 'README.md', 'README.md', 0)
                runner = DocTestRunner()
                runner.run(test)
                assert not runner.failures
