[![Build Status](https://travis-ci.org/saintamh/canif.svg?branch=master)](https://travis-ci.org/saintamh/canif)
[![PyPI version](https://badge.fury.io/py/canif.svg)](https://pypi.org/project/canif/)

Parser and pretty-printer for JSON and JSON-ish data, on the command line or as a Python library.


Synopsis
========

Suppose you have a JavaScript object literal:

```console
$ cat input.js
setConfig({editable: true, latlng: new LatLng(48.1434, 17.1082), last_modified: new Date(1995, 11, 17)})
```

or a Python `repr` expression:

```console
$ cat input.py
{"_id": 73, "occur": OrderedDict([("doc1", 10), ("doc2", 1)]), "match": <_sre.SRE_Match object at 0x7f2b9eaa5f80>}
```

or a MongoDB document:

```console
$ cat input.mongo
{"id": ObjectId("507f191e810c19729de860ea"), "last_modified": ISODate("2020-05-20T00:00:00Z")}
```

You can use the `canif` library to load up that data as Plain Old Data Structures:

```pycon
>>> with open('input.js', 'rt', encoding='UTF-8') as file_in:
...    canif.load(file_in)
{'$$setConfig': [{'editable': True, 'latlng': {'$$new LatLng': [48.1434, 17.1082]}, 'last_modified': {'$$new Date': [1995, 11, 17]}}]}
```

```pycon
>>> with open('input.py', 'rt', encoding='UTF-8') as file_in:
...    canif.load(file_in)
{'_id': 73, 'occur': {'$$OrderedDict': [[('doc1', 10), ('doc2', 1)]]}, 'match': '$repr<_sre.SRE_Match object at 0x7f2b9eaa5f80>'}
```

```pycon
>>> with open('input.mongo', 'rt', encoding='UTF-8') as file_in:
...    canif.load(file_in)
{'id': {'$oid': ['507f191e810c19729de860ea']}, 'last_modified': {'$$ISODate': ['2020-05-20T00:00:00Z']}}
```

Think of it as a version of `json.loads` that accepts a wider syntax. 

This can be useful when writing Web scrapers, as it allows you to parse JavaScript data structures without having to use a
JavaScript interpreter or a full-blown syntax parser.


Command line usage
==================

You can also use the `canif` command-line tool to pretty-print JSON-ish data:

```console
$ canif < input.js
setConfig(
    {
        editable: true,
        latlng: new LatLng(
            48.1434,
            17.1082,
        ),
        last_modified: new Date(
            1995,
            11,
            17,
        ),
    },
)
```

```console
$ canif < input.py
{
    "_id": 73,
    "occur": OrderedDict(
        [
            (
                "doc1",
                10,
            ),
            (
                "doc2",
                1,
            ),
        ],
    ),
    "match": <_sre.SRE_Match object at 0x7f2b9eaa5f80>,
}
```

```console
$ canif < input.mongo
{
    "id": ObjectId(
        "507f191e810c19729de860ea",
    ),
    "last_modified": ISODate(
        "2020-05-20T00:00:00Z",
    ),
}
```

There's an option to convert the data to proper JSON:

```console
$ canif -j < input.js
{
    "$$setConfig": [
        {
            "editable": true,
            "latlng": {
                "$$new LatLng": [
                    48.1434,
                    17.1082
                ]
            },
            "last_modified": {
                "$$new Date": [
                    1995,
                    11,
                    17
                ]
            }
        }
    ]
}
```

The program pretty-prints the data as it loads it, so it should be able to handle very large files.

Use `--help` for a quick rundown of available options:

```console
$ canif --help
usage: canif [-h] [-i N | -f] [-j] [-T] [--ensure-ascii]
             [-I ENCODING] [-O ENCODING]

Pretty-print JSON and JSON-ish data

optional arguments:
  -h, --help            show this help message and exit
  -i N, --indent N      Indent each level by N spaces (0 means flat,
                        single-line output)
  -f, --flatten         Flatten output (equivalent to -i 0)
  -j, --json-output     Convert data to valid JSON if it wasn't
                        already (e.g. None becomes null)
  -T, --no-trailing-commas
                        Don't insert trailing commas after the last
                        item in a sequence. This is implied by
                        --json-output.
  --ensure-ascii        Ensure JSON output is ASCII by using \uXXXX
                        sequences in place of non-ASCII characters
  -I ENCODING, --input-encoding ENCODING
                        Character set used for decoding the input
                        (default: UTF-8)
  -O ENCODING, --output-encoding ENCODING
                        Character set used for encoding the output
                        (default: UTF-8)
```


Emacs bindings
==============

If you happen to use Emacs' `shell-mode`, this can be very useful to format the logs or output of any Python program.

See [canif.el](emacs/canif.el) for a simple function that you can bind to a keystroke and that will pretty-print the data structure
at point.


Supported formats
=================

Canif is for "JSON and JSON-ish" data. It can parse:

* plain JSON
* JavaScript object literals, including:
  * unquoted keys
  * trailing commas
  * `//` comments
  * empty array slots (e.g. `[1,,,4]`)
* printed Python data structures, including
  * sets: `{42}`
  * tuples: `("one", "two", "three")`
  * `<repr>` representations 
* MongoDB BSON

The parsed data can be pretty-printed in a couple formats:

* verbatim (i.e. only whitespace and commas are modified)
* strict JSON

There are options to control the output, e.g. indent depth, trailing commas, etc.
