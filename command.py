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
        value['states'].sort()
        value['letters'].sort()
        value['transition_function'].sort()
        value['start_states'].sort()
        value['final_states'].sort()
        value = {k:v for (k,v) in sorted(value.items())}
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

    def as_private_re(self) -> str:
        if isinstance(self.value_, frozen_fa):
            assert False
        else:
            return self.value_

    def as_private_fa(self) -> fa.FA:
        if isinstance(self.value_, frozen_fa):
            return fa.json_to_fa(json.loads(self.value_.to_json_str()))
        assert False

    def letters(self) -> str:
        if isinstance(self.value_, frozen_fa):
            return ''.join(self.value_.letters)
        assert False

    @staticmethod
    def from_private_fa(a: fa.FA, letters: str) -> fa_or_re:
        return fa_or_re(
            frozen_fa.from_json_str(
                json.dumps(
                    fa.fa_to_json(a, letters)
                )
            )
        )

    @staticmethod
    def from_private_re(a: str, letters: str) -> fa_or_re:
        return fa_or_re(a)

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
        return super().__call__(value) and validate.fa_has_no_eps(value.as_private_fa())


class IsDeterministic(HasNoEps):
    def __call__(self, value: fa_or_re) -> bool:
        return super().__call__(value) and validate.fa_is_det(value.as_private_fa())


class IsFull(IsDeterministic):
    def __call__(self, value: fa_or_re) -> bool:
        return super().__call__(value) and validate.fa_is_full(value.as_private_fa(), value.letters())


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
    're-to-eps-nfa':        command_line_operation(name='re-to-eps-nfa',       preconditions=(IsRE(),),            postconditions=(IsFA(),)),
    'remove-eps':           command_line_operation(name='remove-eps',          preconditions=(IsFA(),),            postconditions=(HasNoEps(),)),
    'make-deterministic':   command_line_operation(name='make-deterministic',  preconditions=(HasNoEps(),),        postconditions=(IsDeterministic(),)),
    'make-full':            command_line_operation(name='make-full',           preconditions=(IsDeterministic(),), postconditions=(IsFull(),)),
    'minimize':             command_line_operation(name='minimize',            preconditions=(IsFull(),),          postconditions=(IsFull(),)),
    'invert':               command_line_operation(name='invert',              preconditions=(IsFull(),),          postconditions=(IsFull(),)),
    'eps-nfa-to-re':        command_line_operation(name='eps-nfa-to-re',       preconditions=(IsFA(),),            postconditions=(IsRE(),)),
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
            print(
                f'FA has letters {missing_letters!r} missing in command line arguments.', file=stderr)
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
            assert precondition(value)

        func = typing.cast(
            typing.Callable[[fa_or_re, str], fa_or_re],
            eval(
                operation.name.replace('-', '_')
            )
        )

        value = (
            func(
                value,
                letters
            )
        )

        if value.is_fa():
            missing_letters = ''.join([
                letter
                for letter in value.letters()
                if letter not in letters
            ])
            if missing_letters:
                print(
                    f'FA has letters {missing_letters!r} missing in command line arguments.', file=stderr)
                return 1

        for postcondition in operation.postconditions:
            assert postcondition(value)

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


def re_to_eps_nfa(value: fa_or_re, letters: str) -> fa_or_re:

    text = value.as_private_re()
    s = convert.regex_to_ast(text)
    a = convert.ast_to_eps_nfa(s)

    return fa_or_re.from_private_fa(a, letters)


def remove_eps(value: fa_or_re, letters: str) -> fa_or_re:

    a = value.as_private_fa()

    a = convert.remove_eps(a)

    return fa_or_re.from_private_fa(a, letters)


def make_deterministic(value: fa_or_re, letters: str) -> fa_or_re:

    a = value.as_private_fa()

    a = convert.make_deterministic(a)

    return fa_or_re.from_private_fa(a, letters)


def make_full(value: fa_or_re, letters: str) -> fa_or_re:

    a = value.as_private_fa()

    a = convert.make_full(a, letters + letters[0][:0])

    return fa_or_re.from_private_fa(a, letters)


def minimize(value: fa_or_re, letters: str) -> fa_or_re:

    a = value.as_private_fa()

    a = convert.make_min(a)

    return fa_or_re.from_private_fa(a, letters)


def invert(value: fa_or_re, letters: str) -> fa_or_re:

    a = value.as_private_fa()

    a = convert.invert_full_fa(a)

    return fa_or_re.from_private_fa(a, letters)


def eps_nfa_to_re(value: fa_or_re, letters: str) -> fa_or_re:

    a = value.as_private_fa()

    s = convert.fa_to_re(a)

    return fa_or_re.from_private_re(s, letters)



if __name__ == '__main__':
    exit(main(sys.argv, sys.stdin, sys.stdout, sys.stderr))
