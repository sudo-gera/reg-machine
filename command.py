import convert
import sys
import typing
import traceback
import contextlib
from collections import defaultdict as dd
import json
import io
from dataclasses import dataclass

from utils import *
import fa
import argparse

possible_actions = [
    'reg-to-eps-nfa', 'remove-eps', 'make-deterministic', 'make-full',
    'make-min', 'invert', 'nfa-to-reg'
]


def process_args(
    argv: list[str],
    stdin: typing.IO[str],
    stdout: typing.IO[str],
    stderr: typing.IO[str],
) -> int:
    parser = ThrowingArgumentParser(exit_on_error=False)
    parser.add_argument('--input-mode', choices=['reg', 'fa'], required=True)
    parser.add_argument('--actions',
                        choices=possible_actions,
                        required=True,
                        nargs='*')
    parser.add_argument('--letters', required=True)
    try:
        args = parser.parse_args(argv[1:])
    except Exception as e:
        print(e, file=stderr)
        return 1

    input_mode = typing.cast(str, args.input_mode)
    actions = typing.cast(str, args.actions)
    letters = typing.cast(str, args.letters)

    if input_mode == 'fa':
        try:
            value = fa.json_to_dimple(json.loads(stdin.read()))
        except Exception as e:
            print(f'{e!r}', file=stderr)
            return 1
    else:
        value = stdin.read()

    for action in actions:
        if action not in possible_actions:
            print(f'Unknown action: {action!r}')
            return 1

    def reg_to_eps_nfa(value: str) -> str:
        stdin = io.StringIO()
        stdin.write(value)
        stdin.seek(0)
        stdout = io.StringIO()
        stderr = io.StringIO()
        rc = old_main(['-', 'reg', 'eps-non-det-fsm', letters], stdin, stdout,
                      stderr)
        stdout.seek(0)
        stderr.seek(0)
        stdout_data = stdout.read()
        stderr_data = stderr.read()
        if rc:
            print(stdout_data)
            print(stderr_data)
        assert rc == 0
        assert stderr_data == ''
        return stdout_data

    def remove_eps(value: str) -> str:
        stdin = io.StringIO()
        stdin.write(value)
        stdin.seek(0)
        stdout = io.StringIO()
        stderr = io.StringIO()
        rc = old_main(['-', 'eps-non-det-fsm', 'non-det-fsm', letters], stdin,
                      stdout, stderr)
        stdout.seek(0)
        stderr.seek(0)
        stdout_data = stdout.read()
        stderr_data = stderr.read()
        if rc:
            print(stdout_data)
            print(stderr_data)
        assert rc == 0
        assert stderr_data == ''
        return stdout_data

    def make_deterministic(value: str) -> str:
        stdin = io.StringIO()
        stdin.write(value)
        stdin.seek(0)
        stdout = io.StringIO()
        stderr = io.StringIO()
        rc = old_main(['-', 'non-det-fsm', 'det-fsm', letters], stdin, stdout,
                      stderr)
        stdout.seek(0)
        stderr.seek(0)
        stdout_data = stdout.read()
        stderr_data = stderr.read()
        if rc:
            print(stdout_data)
            print(stderr_data)
        assert rc == 0
        assert stderr_data == ''
        return stdout_data

    def make_full(value: str) -> str:
        stdin = io.StringIO()
        stdin.write(value)
        stdin.seek(0)
        stdout = io.StringIO()
        stderr = io.StringIO()
        rc = old_main(['-', 'det-fsm', 'full-det-fsm', letters], stdin, stdout,
                      stderr)
        stdout.seek(0)
        stderr.seek(0)
        stdout_data = stdout.read()
        stderr_data = stderr.read()
        if rc:
            print(stdout_data)
            print(stderr_data)
        assert rc == 0
        assert stderr_data == ''
        return stdout_data

    def make_min(value: str) -> str:
        stdin = io.StringIO()
        stdin.write(value)
        stdin.seek(0)
        stdout = io.StringIO()
        stderr = io.StringIO()
        rc = old_main(['-', 'full-det-fsm', 'min-full-det-fsm', letters],
                      stdin, stdout, stderr)
        stdout.seek(0)
        stderr.seek(0)
        stdout_data = stdout.read()
        stderr_data = stderr.read()
        if rc:
            print(stdout_data)
            print(stderr_data)
        assert rc == 0
        assert stderr_data == ''
        return stdout_data

    def invert(value: str) -> str:
        stdin = io.StringIO()
        stdin.write(value)
        stdin.seek(0)
        stdout = io.StringIO()
        stderr = io.StringIO()
        rc = old_main(
            ['-', 'min-full-det-fsm', 'invert-min-full-det-fsm', letters],
            stdin, stdout, stderr)
        stdout.seek(0)
        stderr.seek(0)
        stdout_data = stdout.read()
        stderr_data = stderr.read()
        if rc:
            print(stdout_data)
            print(stderr_data)
        assert rc == 0
        assert stderr_data == ''
        return stdout_data

    for action in actions:
        # print(f'{action = !r}, {value = !r}')
        value = eval(action.replace('-', '_'))(value)

    # print(repr(value))

    value = value[1:]

    print(json.dumps(fa.dimple_to_json(value, letters), indent=4))
    return 0


def main(
    argv: list[str],
    stdin: typing.IO[str],
    stdout: typing.IO[str],
    stderr: typing.IO[str],
) -> int:
    with (
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
    ):
        return process_args(argv, stdin, stdout, stderr)


def old_main(
    argv: list[str],
    stdin: typing.IO[str],
    stdout: typing.IO[str],
    stderr: typing.IO[str],
) -> int:
    with (
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
    ):
        return old_old_main(argv, stdin, stdout, stderr)


def old_old_main(
    argv: list[str],
    stdin: typing.IO[str],
    stdout: typing.IO[str],
    stderr: typing.IO[str],
) -> int:

    if len(argv) not in [3, 4]:
        print(f'usage: {argv[0]} <input format> <output format> [<labels>]',
              file=stderr)
        return 1

    if len(argv) == 3:
        [*formats, labels] = [*argv[1:], '']
    else:
        [*formats, labels] = [*argv[1:]]

    all_formats: dict[str, typing.Callable[[fa.FA], fa.FA]] = {
        'reg': lambda a: a,
        'eps-non-det-fsm': convert.remove_eps,
        'non-det-fsm': convert.make_deterministic,
        'det-fsm': lambda a: convert.make_full(a, labels + labels[0][:0]),
        'full-det-fsm': convert.make_min,
        'min-full-det-fsm': convert.invert_full_fa,
        'invert-full-det-fsm': lambda a: a,
    }

    for arg in formats:
        if arg not in all_formats:
            print(f'unknown format: {arg}.', file=stderr)
            print('supported formats are:', file=stderr)
            for f in all_formats:
                print(f'    {f}', file=stderr)
            return 1

    format_indexes = [[*all_formats].index(f) for f in formats]

    if format_indexes[0] > format_indexes[1]:
        print('this conversion order is not supported.', file=stderr)
        return 1

    try:
        if formats[0] == 'reg':
            text = stdin.readline()
            if text[-1] == '\n':
                text = text[:-1]
            if formats[1] == 'reg':
                print(text, file=stdout)
                return 0
            else:
                s = convert.regex_to_ast(text)
                a = convert.ast_to_eps_nfa(s)
        else:
            text = stdin.read()
            a = fa.from_dimple(text)

        for num in range(*format_indexes):
            func = [*all_formats.values()][num]
            if func.__closure__ is not None and not labels:
                print('labels argument is undefined.', file=stderr)
                return 1
            a = func(a)

        print(file=stdout)
        print(fa.dimple(a), end='', file=stdout)
        return 0
    except Exception:
        print('Incorrect input data.', file=stderr)
        # print(traceback.format_exc(), file=debug)
        return 1


if __name__ == '__main__':
    # exit(old_main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
    exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
