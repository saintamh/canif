#!/usr/bin/env python3

# standards
from os import path
import setuptools


with open(path.join(path.dirname(__file__), 'README.md'), 'rb') as file_in:
    long_description = file_in.read().decode('UTF-8')


setuptools.setup(
    name='canif',
    version='0.1.0',
    author='Hervé Saint-Amand',
    author_email='canif@saintamh.org',
    description='Pretty-printer for JSON and JSON-like data',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/saintamh/canif/',
    packages=['canif'],
    entry_points={
        'console_scripts': [
            'canif = canif:main',
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
