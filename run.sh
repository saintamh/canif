#!/bin/bash

cd $(dirname $(realpath "$0")) \
   && python3 -m canif.cli "$@"
