#!/bin/bash

set -e

cd $(dirname $(realpath "$0"))
. venv-canif/bin/activate
canif "$@"
