#!/bin/bash

# Use the latest available Python interpreter
python=$(compgen -c | grep -E '^python3[0-9\.]+$' | sort -g | tail -1)

cd $(dirname $(realpath "$0")) \
   && $python -m canif.cli "$@"
