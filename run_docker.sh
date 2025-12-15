#!/usr/bin/env bash
set -x -u -e -o pipefail

cd "$(
    dirname "$(
        realpath "$0"
    )"
)"

docker container stop state_machine || true
docker container rm state_machine || true
docker image rm state_machine || true

# docker build --platform linux/x86_64 -t state_machine .
docker build -t state_machine .
docker container run --rm -i -t --name state_machine state_machine

docker container stop state_machine
docker container rm state_machine
docker image rm state_machine
