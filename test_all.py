from __future__ import annotations
from utils import debug
import command
import convert
import fa
from dataclasses import dataclass
import functools
from copy import deepcopy as cp
import random
import re
from collections import defaultdict as dd
import time
import ast
import sys
import io
import validate
pytest = __import__('pytest')


class InternalTestError(Exception):
    pass


def can_fa_eval_string(a: fa.FA, path: str, limit: int = 64) -> bool:
    operation_count = 0
    accessible_by_eps_from_this_node = {
        node: list(node.bfs(True)) for node in a.start.bfs()}
    current_nodes = list(a.start.bfs(True))
    for c in path:
        next_nodes: dict[fa.Node, None] = {}
        for current_node in current_nodes:
            for next_nodes_from_one_current_node in current_node.next_nodes_by_label[c]:
                next_nodes |= dict.fromkeys(
                    accessible_by_eps_from_this_node[next_nodes_from_one_current_node])
                operation_count += 1
                if operation_count > limit:
                    raise InternalTestError
        current_nodes = list(next_nodes)
    res = any([a.is_final(n) for n in current_nodes])
    return res


FA = fa.FA


@dataclass(frozen=True)
class created_random_fa:
    fa: fa.FA
    random_string_that_matches: str | None
    regex_for_fullmatch: str | None
    random_strings_that_maybe_match: list[str | None]
    regex_for_converting_to_fa: str

    @functools.cached_property
    def compiled_regex_for_fullmatch(self) -> re.Pattern[str]:
        if self.regex_for_fullmatch is not None:
            return re.compile(self.regex_for_fullmatch)
        raise InternalTestError


def random_fa(
        rand: random.Random,
        depth: int,
        labels: str,  # allowed letters
) -> created_random_fa:
    n = rand.randint(0, 7)
    n *= bool(depth)
    if n == 0:
        arg = rand.choice([None, '', *list(labels)])
        return created_random_fa(
            fa.FA(arg),
            arg,
            arg,
            [rand.choice([None, '', *list(labels)]) for q in range(9)],
            (
                '0'
                if arg is None else
                '1'
                if arg == '' else
                arg
            ),
        )
    elif n < 3:
        left = random_fa(rand, depth - 1, labels)
        right = random_fa(rand, depth - 1, labels)
        if left.random_string_that_matches is None:
            return created_random_fa(
                left.fa + right.fa,
                right.random_string_that_matches,
                right.regex_for_fullmatch,
                right.random_strings_that_maybe_match,
                f'({left.regex_for_converting_to_fa} + {right.regex_for_converting_to_fa})',
            )
        if right.random_string_that_matches is None:
            return created_random_fa(
                left.fa + right.fa,
                left.random_string_that_matches,
                left.regex_for_fullmatch,
                left.random_strings_that_maybe_match,
                f'({left.regex_for_converting_to_fa} + {right.regex_for_converting_to_fa})',
            )
        return created_random_fa(
            left.fa + right.fa,
            rand.choice([
                left.random_string_that_matches,
                right.random_string_that_matches
            ]),
            f'({left.regex_for_fullmatch}|{right.regex_for_fullmatch})',
            [
                rand.choice([
                    left.random_strings_that_maybe_match[q],
                    right.random_strings_that_maybe_match[q]
                ]) for q in range(9)
            ],
            f'({left.regex_for_converting_to_fa} + {right.regex_for_converting_to_fa})',
        )
    elif n < 7:
        left = random_fa(rand, depth - 1, labels)
        right = random_fa(rand, depth - 1, labels)
        if left.random_string_that_matches is None or left.regex_for_fullmatch is None or right.random_string_that_matches is None or right.regex_for_fullmatch is None:
            return created_random_fa(
                left.fa * right.fa,
                None,
                None,
                [
                    rand.choice([
                        left.random_strings_that_maybe_match[q],
                        right.random_strings_that_maybe_match[q]
                    ]) for q in range(9)
                ],
                f'({left.regex_for_converting_to_fa} * {right.regex_for_converting_to_fa})',
            )
        else:
            return created_random_fa(
                left.fa * right.fa,
                left.random_string_that_matches +
                right.random_string_that_matches,
                left.regex_for_fullmatch + right.regex_for_fullmatch,
                [
                    rand.choice([
                        left.random_strings_that_maybe_match[q],
                        right.random_strings_that_maybe_match[q],
                        left.random_string_that_matches +
                        right.random_string_that_matches
                    ]) for q in range(9)
                ],
                f'({left.regex_for_converting_to_fa} * {right.regex_for_converting_to_fa})',
            )
    elif n == 7:
        right_n = rand.choice([*range(-2, 3)])
        left = random_fa(rand, depth - 1, labels)
        if right_n < 0:
            return created_random_fa(
                ~left.fa,
                left.random_string_that_matches * -right_n
                if left.random_string_that_matches is not None else '',
                f'({left.regex_for_fullmatch})*'
                if left.regex_for_fullmatch is not None else '',
                [
                    left.random_strings_that_maybe_match[q] * -right_n if
                    left.random_strings_that_maybe_match[q] is not None else ''
                    for q in range(9)
                ],
                f'({left.regex_for_converting_to_fa}) ** None',
            )
        elif right_n > 0:
            return created_random_fa(
                left.fa ** right_n,
                left.random_string_that_matches * right_n
                if left.random_string_that_matches is not None else None,
                left.regex_for_fullmatch *
                right_n if left.regex_for_fullmatch is not None else None,
                [
                    left.random_strings_that_maybe_match[q] * -right_n if
                    left.random_strings_that_maybe_match[q] is not None else ''
                    for q in range(9)
                ],
                f'({left.regex_for_converting_to_fa}) ** {right_n}',
            )
        else:
            return created_random_fa(
                left.fa**right_n,
                '',
                '',
                [
                    left.random_strings_that_maybe_match[q] * abs(right_n) if
                    left.random_strings_that_maybe_match[q] is not None else ''
                    for q in range(9)
                ],
                f'({left.regex_for_converting_to_fa}) ** {right_n}',
            )
    assert False


def graphviz(a: fa.FA) -> str:
    id_map: dd[fa.Node, int] = dd(lambda: len(id_map))
    res = 'digraph G{\n'
    for n in a.start.bfs():
        res += f'    {id_map[n]} [ label = "{id_map[n]} {n.is_final or n == a.the_only_final_if_exists_or_unrelated_node}" ]\n'
    for n in a.start.bfs():
        for label, nl in n.next_nodes_by_label.items():
            for nn in nl:
                res += f'    {id_map[n]} -> {id_map[nn]} [ label = "{label}" ]\n'
    res += '}'
    return res


def test_fa_simple_bfs() -> None:
    f = fa.FA()
    assert list(f.start.bfs()) == [f.start]

    f = fa.FA(None)
    assert list(f.start.bfs()) == [f.start]

    f = fa.FA('')
    assert list(f.start.bfs()) == [
        f.start, f.the_only_final_if_exists_or_unrelated_node
    ]

    f = fa.FA('A')
    assert list(f.start.bfs()) == [
        f.start, f.the_only_final_if_exists_or_unrelated_node
    ]

    assert not can_fa_eval_string(fa.FA(None), '')
    assert not can_fa_eval_string(fa.FA(None), 'A')
    assert can_fa_eval_string(fa.FA(''), '')
    assert not can_fa_eval_string(fa.FA(''), 'A')
    assert not can_fa_eval_string(fa.FA('A'), '')
    assert can_fa_eval_string(fa.FA('A'), 'A')

    assert can_fa_eval_string(fa.FA('A') + fa.FA('B'), 'A')
    assert can_fa_eval_string(fa.FA('A') + fa.FA('B'), 'B')
    assert not can_fa_eval_string(fa.FA('A') + fa.FA('B'), '')
    assert not can_fa_eval_string(fa.FA('A') + fa.FA('B'), 'BA')
    assert not can_fa_eval_string(fa.FA('A') + fa.FA('B'), 'AB')

    assert not can_fa_eval_string(fa.FA('A') * fa.FA('B'), 'A')
    assert not can_fa_eval_string(fa.FA('A') * fa.FA('B'), 'B')
    assert not can_fa_eval_string(fa.FA('A') * fa.FA('B'), '')
    assert not can_fa_eval_string(fa.FA('A') * fa.FA('B'), 'BA')
    assert can_fa_eval_string(fa.FA('A') * fa.FA('B'), 'AB')

    assert can_fa_eval_string(~fa.FA('A'), '')
    assert can_fa_eval_string(~fa.FA('A'), 'A')
    assert can_fa_eval_string(~fa.FA('A'), 'AA')
    assert not can_fa_eval_string(~fa.FA('A'), 'B')
    assert not can_fa_eval_string(~fa.FA('A'), 'AB')
    assert not can_fa_eval_string(~fa.FA('A'), 'BA')


def check_equal(a: fa.FA, s: fa.FA) -> None:
    a_to_s: dict[fa.Node, fa.Node] = {
        d: f
        for d, f in zip(a.start.bfs(), s.start.bfs())
    }
    s_to_a: dict[fa.Node, fa.Node] = {
        d: f
        for d, f in zip(s.start.bfs(), a.start.bfs())
    }
    assert len(list(a.start.bfs())) == len(list(
        s.start.bfs())) == len(a_to_s) == len(s_to_a)
    assert [*a.start.bfs()] == [*a_to_s.keys()] == [*s_to_a.values()]
    assert [*s.start.bfs()] == [*s_to_a.keys()] == [*a_to_s.values()]

    def check_a_to_s(a_to_s: dict[fa.Node, fa.Node],
                     s_to_a: dict[fa.Node, fa.Node]) -> None:
        for d, f in a_to_s.items():
            assert a_to_s[d] == f
            for l in d.next_nodes_by_label:
                assert {a_to_s[n]
                        for n in d.next_nodes_by_label[l]
                        } == set(f.next_nodes_by_label[l])

    check_a_to_s(a_to_s, s_to_a)
    check_a_to_s(s_to_a, a_to_s)


def test_io() -> None:
    assert fa.dimple(fa.FA('-') *
            fa.FA('+')) == '1\n\n4\n\n1 2 -\n2 3 \n3 4 +\n'
    check_equal(
        fa.FA('-') * fa.FA('+'),
        fa.from_dimple('1\n\n2\n\n1 3 -\n3 4 \n4 2 +\n'))

    def test_main(argv: list[str],
                  text_in: str,
                  text_out: str,
                  code: int,
                  text_err: str = '') -> None:
        stdin = io.StringIO()
        stdin.write(text_in)
        stdin.seek(0)
        stdout = io.StringIO()
        stderr = io.StringIO()
        rc = command.old_main(argv, stdin, stdout, stderr)
        stdout.seek(0)
        stderr.seek(0)
        try:
            assert code == rc
            assert stdout.read() == text_out
            assert stderr.read() == text_err
        except AssertionError:
            print(f'{rc = }', file=debug)
            print(f'{text_out = }', file=debug)
            print(f'{text_err = }', file=debug)
            raise

    test_main(['command.py'], '',
              'usage: command.py <input format> <output format> [<labels>]\n',
              1)
    test_main(['command.py', 'reg', 'reg'], '0\n', '0\n', 0)
    test_main(
        ['command.py', 'reg', 'peg'], '',
        'unknown format: peg.\nsupported formats are:\n    reg\n    eps-non-det-fsm\n    non-det-fsm\n    det-fsm\n    full-det-fsm\n    min-full-det-fsm\n    invert-full-det-fsm\n',
        1)
    test_main(['command.py', 'det-fsm', 'reg'], '',
              'this conversion order is not supported.\n', 1)
    test_main(['command.py', 'reg', 'det-fsm'], '0', '\n1\n\n\n', 0)
    test_main(['command.py', 'eps-non-det-fsm', 'det-fsm'], '\n1\n\n\n',
              '\n1\n\n\n', 0)
    test_main(['command.py', 'reg', 'full-det-fsm'], '0',
              'labels argument is undefined.\n', 1)
    test_main(
        ['command.py', 'non-det-fsm', 'min-full-det-fsm', 'ab'],
        '0\n\n3\n\n0 3 a\n3 3 a\n3 3 b\n0 1 b\n2 3 a\n2 1 b\n1 2 b\n1 1 a\n',
        '\n1\n\n2\n\n1 2 a\n1 3 b\n2 2 a\n2 2 b\n3 1 b\n3 3 a\n', 0)
    test_main(['command.py', 'reg', 'det-fsm'], '', 'Incorrect input data.\n',
              1)


# seed = 3099010176601051186
seed = random.randint(0, 1 << 64 - 1)
print(f'{seed = }', file=debug)
rand = random.Random(seed)
# print(f'{seed = }', file=open('/dev/tty', 'w'))

arg_values = [*range(99)]
arg_values = [*range(-len(arg_values), len(arg_values)+1)]
rand.shuffle(arg_values)


def test_fa_stress(arg: int) -> None:
    labels = 'qwertyuiop'
    while True:
        try:
            try:
                r = random_fa(rand, 8 if arg < 0 else 10, labels)
            except RecursionError:
                raise InternalTestError
            fa_or_none: fa.FA | None = None
            eps_nfa = nfa = dfa = full_dfa = min_full_dfa = same_min_dfa = inverted_full_dfa = inverted_min_dfa = inverted_same_min_dfa = fa_or_none
            try:
                z = convert.regex_to_ast(r.regex_for_converting_to_fa)
                eps_nfa = convert.ast_to_eps_nfa(z)

                nfa = convert.remove_eps(eps_nfa)
                assert not validate.fa_has_eps(nfa)

                dfa = convert.make_deterministic(nfa)
                assert validate.fa_is_det(dfa)

                full_dfa = convert.make_full(dfa, labels)
                assert validate.fa_is_full(full_dfa, labels)

                min_full_dfa = convert.make_min(full_dfa)
                assert validate.fa_is_full(min_full_dfa, labels)

                same_min_dfa = convert.make_min(min_full_dfa)
                assert validate.fa_is_full(same_min_dfa, labels)
                check_equal(min_full_dfa, same_min_dfa)

                inverted_full_dfa = convert.invert_full_fa(full_dfa)
                assert validate.fa_is_full(inverted_full_dfa, labels)

                inverted_min_dfa = convert.invert_full_fa(min_full_dfa)
                assert validate.fa_is_full(inverted_min_dfa, labels)

                inverted_same_min_dfa = convert.invert_full_fa(same_min_dfa)
                assert validate.fa_is_full(inverted_same_min_dfa, labels)
                check_equal(inverted_min_dfa, inverted_same_min_dfa)

            except RecursionError:
                for var in [
                        eps_nfa, nfa, dfa, full_dfa, min_full_dfa,
                        same_min_dfa, inverted_full_dfa,
                        inverted_min_dfa, inverted_same_min_dfa
                ][::-1]:
                    if var is not None:
                        print(graphviz(var), file=debug)
                        break
                raise
            if r.random_string_that_matches is None:
                raise InternalTestError
            assert r.random_string_that_matches is not None

            if arg < 0:
                assert can_fa_eval_string(r.fa, r.random_string_that_matches)
                assert can_fa_eval_string(eps_nfa,
                                          r.random_string_that_matches)
                assert can_fa_eval_string(nfa, r.random_string_that_matches)
                assert can_fa_eval_string(dfa, r.random_string_that_matches)
                assert can_fa_eval_string(full_dfa,
                                          r.random_string_that_matches)
                assert can_fa_eval_string(min_full_dfa,
                                          r.random_string_that_matches)
            assert can_fa_eval_string(same_min_dfa,
                                      r.random_string_that_matches)
            if arg < 0:
                assert not can_fa_eval_string(inverted_full_dfa,
                                              r.random_string_that_matches)
                assert not can_fa_eval_string(inverted_min_dfa,
                                              r.random_string_that_matches)
                assert not can_fa_eval_string(inverted_same_min_dfa,
                                              r.random_string_that_matches)
            assert re.fullmatch(r.compiled_regex_for_fullmatch,
                                r.random_string_that_matches)
            for t in r.random_strings_that_maybe_match:
                if t is not None:
                    u = can_fa_eval_string(same_min_dfa, t)
                    assert u == bool(re.fullmatch(
                        r.compiled_regex_for_fullmatch, t))
                    if arg < 0:
                        assert can_fa_eval_string(r.fa, t) == u
                        assert can_fa_eval_string(eps_nfa, t) == u
                        assert can_fa_eval_string(nfa, t) == u
                        assert can_fa_eval_string(dfa, t) == u
                        assert can_fa_eval_string(full_dfa, t) == u
                        assert can_fa_eval_string(min_full_dfa, t) == u
                        assert can_fa_eval_string(same_min_dfa, t) == u
                        assert can_fa_eval_string(inverted_full_dfa, t) != u
                        assert can_fa_eval_string(inverted_min_dfa,
                                                  t) != u
                        assert can_fa_eval_string(inverted_same_min_dfa,
                                                  t) != u
            break
        except InternalTestError:
            continue


test_fa_stress = pytest.mark.parametrize('arg', arg_values)(test_fa_stress)
