#!/bin/sh

cd $(dirname "$0")/..
pytest --cov=canif --cov-report=html:coverage/
