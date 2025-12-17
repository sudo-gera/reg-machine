from __future__ import annotations
import abc
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
import validate


@dataclass(frozen=True)
class frozen_fa:
    states: tuple[str]
    letters: tuple[str]
    transition_function: tuple[tuple[str]]
    start_states: tuple[str]
    final_states: tuple[str]

    @staticmethod
    def from_json_str(data: str) -> frozen_fa:
        value = json.loads(data)
        assert isinstance(value, dict)
        return frozen_fa(**value)

    def to_json_str(self) -> str:
        return json.dumps(vars(self), indent=4)


@dataclass(frozen=True)
class fa_or_re:
    value_: str | frozen_fa

    @staticmethod
    def from_public_str(data: str) -> fa_or_re:
        try:
            return fa_or_re(frozen_fa.from_json_str(data))
        except Exception:
            return fa_or_re(data)

    def as_public_str(self) -> str:
        if isinstance(self.value_, frozen_fa):
            return self.value_.to_json_str()
        else:
            return self.value_

    def as_private_str(self) -> str:
        if isinstance(self.value_, frozen_fa):
            return fa.json_to_dimple(json.loads(self.value_.to_json_str()))
        else:
            return self.value_

    def letters(self) -> str:
        if isinstance(self.value_, frozen_fa):
            return ''.join(self.value_.letters)
        assert False

    @staticmethod
    def from_private_str(data: str, letters: str) -> fa_or_re:
        return fa_or_re(frozen_fa.from_json_str(json.dumps(fa.dimple_to_json(data, letters))))

    def is_fa(self) -> bool:
        return isinstance(self.value_, frozen_fa)


class Condition(abc.ABC):
    @abc.abstractmethod
    def __call__(self, value: fa_or_re) -> bool:
        pass


class IsReg(Condition):
    def __call__(self, value: fa_or_re) -> bool:
        return not value.is_fa()


class IsFa(Condition):
    def __call__(self, value: fa_or_re) -> bool:
        return value.is_fa()


class HasNoEps(IsFa):
    def __call__(self, value: fa_or_re) -> bool:
        return validate.fa_has_eps(fa.from_dimple(value.as_private_str()))


class IsDet(HasNoEps):
    def __call__(self, value: fa_or_re) -> bool:
        return validate.fa_is_det(fa.from_dimple(value.as_private_str()))


class IsFull(HasNoEps):
    def __call__(self, value: fa_or_re) -> bool:
        return validate.fa_is_full(fa.from_dimple(value.as_private_str()), value.letters())


@dataclass(frozen=True)
class command_line_action_base:
    name: str
    preconditions: tuple[type[Condition]]
    postconditions: tuple[type[Condition]]
    # action: typing.Callable[[fa_or_re], fa_or_re]


class command_line_action(command_line_action_base):

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> command_line_action:
        if len(args) == 1 and len(kwargs) == 0:
            name = args[0]
            if isinstance(name, str):
                if name in command_line_actions:
                    return command_line_actions[name]
        return super().__new__(cls)
    
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        print(args, kwargs)
        super().__init__(*args, **kwargs)


command_line_actions = {
    'reg-to-eps-nfa':       command_line_action(name='reg-to-eps-nfa',      preconditions=(IsReg,),      postconditions=(IsFa,)),
    'remove-eps':           command_line_action(name='remove-eps',          preconditions=(IsFa,),       postconditions=(HasNoEps,)),
    'make-deterministic':   command_line_action(name='make-deterministic',  preconditions=(HasNoEps,),   postconditions=(IsDet,)),
    'make-full':            command_line_action(name='make-full',           preconditions=(IsDet,),      postconditions=(IsFull,)),
    'minimize':             command_line_action(name='minimize',            preconditions=(IsFull,),     postconditions=(IsFull,)),
    'invert':               command_line_action(name='invert',              preconditions=(IsFull,),     postconditions=(IsFull,)),
    'full-dfa-to-reg':      command_line_action(name='full-dfa-to-reg',     preconditions=(IsFull,),     postconditions=(IsReg,)),
}

# possible_actions = [
#     'reg-to-eps-nfa', 'remove-eps', 'make-deterministic', 'make-full',
#     'make-min', 'invert', 'nfa-to-reg'
# ]


def process_args(
    argv: list[str],
    stdin: typing.IO[str],
    stdout: typing.IO[str],
    stderr: typing.IO[str],
) -> int:

    parser = ThrowingArgumentParser(exit_on_error=False)
    parser.add_argument(
        '--actions',
        choices=[*command_line_actions.values()],
        required=True,
        nargs='*',
        type=command_line_action,
    )
    parser.add_argument('--letters', required=True)

    try:
        args = parser.parse_args(argv[1:])
    except Exception as e:
        print(e, file=stderr)
        return 1

    actions = typing.cast(list[command_line_action], args.actions)
    letters = typing.cast(str, args.letters)

    assert issubclass(IsFull, IsFa)

    for left_action, right_action in zip(actions, actions[1:]):

        for precondition in right_action.preconditions:
            for postcondition in left_action.postconditions:
                if issubclass(postcondition, precondition):
                    break
            else:
                assert False

    try:
        value = fa_or_re.from_public_str(stdin.read())
    except Exception as e:
        print(f'{e!r}', file=stderr)
        return 1

    if actions:
        for precondition in actions[0].preconditions:
            assert precondition()(value)

    for action in actions:
        for precondition in action.preconditions:
            assert precondition()(value)
        value = eval(action.name.replace('-', '_'))(value, letters)

    print(value.as_public_str())

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


def reg_to_eps_nfa(value: str, letters: str) -> str:
    return call_old_main('reg_to_eps_nfa', value, letters)


def remove_eps(value: str, letters: str) -> str:
    return call_old_main('remove_eps', value, letters)


def make_deterministic(value: str, letters: str) -> str:
    return call_old_main('make_deterministic', value, letters)


def make_full(value: str, letters: str) -> str:
    return call_old_main('make_full', value, letters)


def minimize(value: str, letters: str) -> str:
    return call_old_main('minimize', value, letters)


def invert(value: str, letters: str) -> str:
    return call_old_main('invert', value, letters)


new_commands_to_old_commands = {
    'reg_to_eps_nfa':     ('reg',          'eps-non-det-fsm'),

    'remove_eps':         ('eps-non-det-fsm',              'non-det-fsm'),

    'make_deterministic': ('non-det-fsm',                 'det-fsm'),

    'make_full':          ('det-fsm',            'full-det-fsm'),

    'minimize':           ('full-det-fsm',        'min-full-det-fsm'),

    'invert':             ('min-full-det-fsm', 'invert-min-full-det-fsm'),
}


def call_old_main(action: str, stdin_data: str, letters: str) -> str:
    stdin = io.StringIO()
    stdin.write(stdin_data)
    stdin.seek(0)
    stdout = io.StringIO()
    stderr = io.StringIO()
    rc = old_main(
        ['-', *new_commands_to_old_commands[action], letters],
        stdin, stdout, stderr)
    stdout.seek(0)
    stderr.seek(0)
    stdout_data = stdout.read()
    stderr_data = stderr.read()
    if rc:
        print(f'{rc = }')
        print(stdout_data)
        print(stderr_data)
    assert rc == 0
    assert stderr_data == ''
    return stdout_data


def old_main(
    argv: list[str],
    stdin: typing.IO[str],
    stdout: typing.IO[str],
    stderr: typing.IO[str],
) -> int:
    # print(argv, stdin.read(), stdin.seek(0))
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
