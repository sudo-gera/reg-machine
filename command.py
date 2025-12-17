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


private_to_public : dict[str, str] = {}
public_to_private : dict[str, str] = {}

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
        private = fa.json_to_dimple(value)
        public = data
        private_to_public[public] = private
        private_to_public[private] = public
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


@dataclass
class Condition(abc.ABC):
    def __call__(self, value: fa_or_re) -> bool:
        return True


class IsRE(Condition):
    def __call__(self, value: fa_or_re) -> bool:
        return super().__call__(value) and not value.is_fa()


class IsFA(Condition):
    def __call__(self, value: fa_or_re) -> bool:
        return super().__call__(value) and value.is_fa()


class HasNoEps(IsFA):
    def __call__(self, value: fa_or_re) -> bool:
        return super().__call__(value) and validate.fa_has_no_eps(fa.dimple_to_fsm(value.as_private_str()))


class IsDeterministic(HasNoEps):
    def __call__(self, value: fa_or_re) -> bool:
        return super().__call__(value) and validate.fa_is_det(fa.dimple_to_fsm(value.as_private_str()))


class IsFull(IsDeterministic):
    def __call__(self, value: fa_or_re) -> bool:
        return super().__call__(value) and validate.fa_is_full(fa.dimple_to_fsm(value.as_private_str()), value.letters())


@dataclass(frozen=True)
class command_line_operation_base:
    name: str
    preconditions: tuple[Condition]
    postconditions: tuple[Condition]


class command_line_operation(command_line_operation_base):

    @staticmethod
    def name_or_none(*args: typing.Any, **kwargs: typing.Any) -> str | None:
        if len(args) == 1 and len(kwargs) == 0:
            name = args[0]
            if isinstance(name, str):
                if name in command_line_operations:
                    return name
        return None

    def __new__(cls, *args: typing.Any, **kwargs: typing.Any) -> command_line_operation:
        name = command_line_operation.name_or_none(*args, **kwargs)
        if name is not None:
            return command_line_operations[name]
        return super().__new__(cls)

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        name = command_line_operation.name_or_none(*args, **kwargs)
        if name is not None:
            return
        super().__init__(*args, **kwargs)


command_line_operations = {
    're-to-eps-nfa':        command_line_operation(name='re-to-eps-nfa',       preconditions=(IsRE(),),      postconditions=(IsFA(),)),
    'remove-eps':           command_line_operation(name='remove-eps',          preconditions=(IsFA(),),       postconditions=(HasNoEps(),)),
    'make-deterministic':   command_line_operation(name='make-deterministic',  preconditions=(HasNoEps(),),   postconditions=(IsDeterministic(),)),
    'make-full':            command_line_operation(name='make-full',           preconditions=(IsDeterministic(),),      postconditions=(IsFull(),)),
    'minimize':             command_line_operation(name='minimize',            preconditions=(IsFull(),),     postconditions=(IsFull(),)),
    'invert':               command_line_operation(name='invert',              preconditions=(IsFull(),),     postconditions=(IsFull(),)),
    'full-dfa-to-re':       command_line_operation(name='full-dfa-to-re',      preconditions=(IsFull(),),     postconditions=(IsRE(),)),
}


def process_args(
    argv: list[str],
    stdin: typing.IO[str],
    stdout: typing.IO[str],
    stderr: typing.IO[str],
) -> int:

    parser = ThrowingArgumentParser(exit_on_error=False)
    parser.add_argument(
        '--operations',
        choices=list(command_line_operations.values()),
        required=True,
        nargs='*',
        type=command_line_operation,
    )
    parser.add_argument('--letters', required=True)

    try:
        args = parser.parse_args(argv[1:])
    except Exception as e:
        print(e, file=stderr)
        return 1

    operations = typing.cast(list[command_line_operation], args.operations)
    letters = typing.cast(str, args.letters)

    assert issubclass(IsFull, IsFA)

    for left_operation, right_operation in zip(operations, operations[1:]):

        for precondition in right_operation.preconditions:
            for postcondition in left_operation.postconditions:
                if issubclass(type(postcondition), type(precondition)):
                    break
            else:
                operation = right_operation
                msg = f'{precondition = } of {operation = } is not fulfilled by postconditions of '
                operation = left_operation
                msg += f'{operation = }.'
                print(msg, file=stderr)
                return 1

    try:
        value = fa_or_re.from_public_str(stdin.read())
    except Exception as e:
        print(f'{e!r}', file=stderr)
        return 1

    if value.is_fa():
        missing_letters = ''.join([
            letter
            for letter in value.letters()
                if letter not in letters
        ])
        if missing_letters:
            print(f'FA has letters {missing_letters!r} missing in command line arguments.', file=stderr)
            return 1

    if operations:
        operation = operations[0]
        for precondition in operation.preconditions:
            if not precondition(value):
                print(
                    f'Input {value!r} dit not pass {precondition = !r} of the {operation = !r}.', file=stderr)
                return 1

    for operation in operations:
        for precondition in operation.preconditions:
            # print(f'{precondition = }', value, file=debug)
            assert precondition(value)
        func = typing.cast(typing.Callable[[str, str], str], eval(
            operation.name.replace('-', '_')))
        value = fa_or_re.from_private_str(
            func(value.as_private_str(), letters)[1:], letters)
        for postcondition in operation.postconditions:
            # print(f'{postcondition = }', value, file=debug)
            assert postcondition(value)

    print(value.as_public_str())

    return 0


def main(
    argv: list[str],
    stdin: typing.IO[str],
    stdout: typing.IO[str],
    stderr: typing.IO[str],
) -> int:
    # print(f'{argv = }', f'{stdin.read() = }', file=debug)
    # stdin.seek(0)
    with (
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
    ):
        return process_args(argv, stdin, stdout, stderr)


def re_to_eps_nfa(value: str, letters: str) -> str:
    return old_main('re_to_eps_nfa', value, letters)


def remove_eps(value: str, letters: str) -> str:
    return old_main('remove_eps', value, letters)


def make_deterministic(value: str, letters: str) -> str:
    return old_main('make_deterministic', value, letters)


def make_full(value: str, letters: str) -> str:
    return old_main('make_full', value, letters)


def minimize(value: str, letters: str) -> str:
    return old_main('minimize', value, letters)


def invert(value: str, letters: str) -> str:
    return old_main('invert', value, letters)


def full_dfa_to_re(value: str, letters: str) -> str:
    return old_main('full_dfa_to_re', value, letters)


new_commands_to_old_commands = {
    're_to_eps_nfa':      ('re_to_eps_nfa',             'remove_eps'),

    'remove_eps':         ('remove_eps',     'make_deterministic'),

    'make_deterministic': ('make_deterministic',             'make_full'),

    'make_full':          ('make_full',            'minimize'),

    'minimize':           ('minimize',        'invert'),

    'invert':             ('invert', 'invert-full-det-fsm'),

    'full_dfa_to_re':     ('todo', 'todo'),
}


def old_main(
    formats_0: str,
    stdin: str,
    letters: str,
) -> str:

    labels = letters

    all_formats: dict[str, typing.Callable[[fa.FA], fa.FA]] = {
        're_to_eps_nfa': lambda a: a,
        'remove_eps': convert.remove_eps,
        'make_deterministic': convert.make_deterministic,
        'make_full': lambda a: convert.make_full(a, labels + labels[0][:0]),
        'minimize': convert.make_min,
        'invert': convert.invert_full_fa,
        'invert-full-det-fsm': lambda a: a,
    }

    if formats_0 == 're_to_eps_nfa':
        text = stdin
        s = convert.regex_to_ast(text)
        a = convert.ast_to_eps_nfa(s)
    else:
        text = stdin
        a = fa.dimple_to_fsm(text)


    func = all_formats[formats_0]
    a = func(a)

    return '\n' + fa.fsm_to_dimple(a)


if __name__ == '__main__':
    # exit(old_main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
    exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
