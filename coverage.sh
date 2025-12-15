#!/usr/bin/env bash

cd "$(
    dirname "$(
        realpath "$0"
    )"
)"

set -e -x -u -o pipefail

coverage run --include="$(find . '!' -name 'test_all.py' -name '*.py' -type f -printf '%p,' | head -c -1)" -m pytest ./test_all.py
coverage html
coverage report

