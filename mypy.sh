#!/usr/bin/env bash

cd "$(
    dirname "$(
        realpath "$0"
    )"
)"

set -e -x -u -o pipefail

for ver in 10 11 12 13
do
    for file in *.py
    do
        python3.$ver -m mypy --strict "$file"
    done
done
