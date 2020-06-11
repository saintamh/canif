#!/usr/bin/env python3

# standards
from os import path
import setuptools


with open(path.join(path.dirname(__file__), 'README.md'), 'rb') as file_in:
    long_description = file_in.read().decode('UTF-8')


setuptools.setup(
    name='canif',
    version='0.3.1',
    author='Hervé Saint-Amand',
    author_email='canif@saintamh.org',
    description='Parser and pretty-printer for JSON and JSON-ish data',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/saintamh/canif/',
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'canif = canif.cli:main',
        ],
    },
    install_requires=[],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development',
        'Topic :: Text Processing',
        'Topic :: Utilities',
    ],
)
