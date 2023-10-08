import convert
import sys
import typing
import traceback
from collections import defaultdict as dd

import fsm


def main(
        argv: list[str],
        stdin: typing.IO[str],
        stdout: typing.IO[str]) -> int:
    if len(argv) not in [3, 4]:
        print(
            f'usage: {argv[0]} <input format> <output format> [<labels>]',
            file=stdout)
        return 1
    if len(argv) == 3:
        [*formats, labels] = [*argv[1:], '']
    else:
        [*formats, labels] = [*argv[1:]]
    all_formats: dict[str, typing.Callable[[fsm.FSM], fsm.FSM]] = {
        'reg': lambda a: a,
        'eps-non-det-fsm': convert.eps_non_det_fsm_to_non_det_fsm,
        'non-det-fsm': convert.non_det_fsm_to_det_fsm,
        'det-fsm': lambda a: convert.det_fsm_to_full_det_fsm(a, labels + labels[0][:0]),
        'full-det-fsm': convert.full_fsm_to_min_full_fsm,
        'min-full-det-fsm': convert.invert_full_fsm,
        'invert-full-det-fsm': lambda a: a,
    }
    for arg in formats:
        if arg not in all_formats:
            print(f'unknown format: {arg}.', file=stdout)
            print('supported formats are:', file=stdout)
            for f in all_formats:
                print(f'    {f}', file=stdout)
            return 1
    format_nums = [[*all_formats].index(f) for f in formats]
    if format_nums[0] > format_nums[1]:
        print('this conversion order is not supported.', file=stdout)
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
                s = convert.reg_to_ast(text)
                a = convert.ast_to_eps_non_det_fsm(s)
        else:
            text = stdin.read()
            a = fsm.FSM.from_dimple(text)
        for num in range(*format_nums):
            func = [*all_formats.values()][num]
            if func.__closure__ is not None and not labels:
                print('labels argument is undefined.', file=stdout)
                return 1
            a = func(a)
        print(file=stdout)
        print(a.dimple(), end='', file=stdout)
        return 0
    except Exception:
        print('Incorrect input data.', file=stdout)
        print(traceback.format_exc())
        return 1


if __name__ == '__main__':
    exit(main(sys.argv, sys.stdin, sys.stdout))
