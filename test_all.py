from __future__ import annotations
import pytest
import fsm
import convert

from copy import deepcopy as cp
import random
import re
from collections import defaultdict as dd
import time
import ast
import sys


def fsm_eval(a: fsm.FSM, path: str):
    ops = 0
    eps_map = {n: list(n.bfs(True)) for n in a.start.bfs()}
    current_nodes = list(a.start.bfs(True))
    next_nodes: dict[fsm.Node, None] = {}
    for c in path:
        for n in current_nodes:
            for nn in n.next[c]:
                next_nodes |= dict.fromkeys(eps_map[nn])
                ops += 1
                if ops > 64:
                    raise TabError
        current_nodes = list(next_nodes)
        next_nodes = {}
    res = any([n.stop or a.stop == n for n in current_nodes])
    return res


def random_fsm(rand: random.Random,
               depth,
               labels # allowed letters
               ) -> tuple[fsm.FSM,
                                 str | None, # random string that matches
                                 str | None, # regex for re.fullmatch
                                 list[str | None], # random strings that maybe match
                                 str | None]: # regex for converting to FSM
    n = rand.randint(0, 7)
    n *= bool(depth)
    if n == 0:
        arg = rand.choice([None, '', *list(labels)])
        return (
            fsm.FSM(arg),
            arg,
            arg,
            [rand.choice([None, '', *list(labels)]) for q in range(9)],
            ({arg: arg} | {None: '0', '': '1'})[arg],
        )
    elif n < 3:
        left = random_fsm(rand, depth - 1, labels)
        right = random_fsm(rand, depth - 1, labels)
        if left[1] is None:
            return (
                left[0] + right[0],
                right[1],
                right[2],
                right[3],
                f'({left[4]} + {right[4]})',
            )
        if right[1] is None:
            return (
                left[0] + right[0],
                left[1],
                left[2],
                left[3],
                f'({left[4]} + {right[4]})',
            )
        return (
            left[0] + right[0],
            rand.choice([left[1], right[1]]),
            f'({left[2]}|{right[2]})',
            [rand.choice([left[3][q], right[3][q]]) for q in range(9)],
            f'({left[4]} + {right[4]})',
        )
    elif n < 7:
        left = random_fsm(rand, depth - 1, labels)
        right = random_fsm(rand, depth - 1, labels)
        if left[1] is None or left[2] is None or right[1] is None or right[2] is None:
            return (
                left[0] * right[0],
                None,
                None,
                [rand.choice([left[3][q], right[3][q]]) for q in range(9)],
                f'({left[4]} * {right[4]})',
            )
        else:
            return (
                left[0] * right[0],
                left[1] + right[1],
                left[2] + right[2],
                [rand.choice([left[3][q], right[3][q], left[1] + right[1]]) for q in range(9)],
                f'({left[4]} * {right[4]})',
            )
    elif n == 7:
        right_n = rand.choice([*range(-2, 3)])
        left = random_fsm(rand, depth - 1, labels)
        if right_n < 0:
            return (
                left[0] ** None,
                left[1] * -right_n if left[1] is not None else '',
                f'({left[2]})*' if left[2] is not None else '',
                [left[3][q] * -right_n if left[3][q] is not None else '' for q in range(9)],
                f'({left[4]}) ** None',
            )
        elif right_n > 0:
            return (
                left[0] ** right_n,
                left[1] * right_n if left[1] is not None else None,
                left[2] * right_n if left[2] is not None else None,
                [left[3][q] * -right_n if left[3][q] is not None else '' for q in range(9)],
                f'({left[4]}) ** {right_n}',
            )
        else:
            return (
                left[0] ** right_n,
                '',
                '',
                [left[3][q] * abs(right_n) if left[3][q] is not None else '' for q in range(9)],
                f'({left[4]}) ** {right_n}',
            )
    assert False


def graphviz(a: fsm.FSM):
    id_map: dd[fsm.Node, int] = dd(lambda: len(id_map))
    res = 'digraph G{\n'
    for n in a.start.bfs():
        res += f'    {id_map[n]} [ label = " {id_map[n]} {n.stop}" ]\n'
    for n in a.start.bfs():
        for label, nl in n.next.items():
            for nn in nl:
                res += f'    {id_map[n]} -> {id_map[nn]} [ label = "{label}" ]\n'
    res += '}'
    return res


def test_fsm_simple_bfs():
    f = fsm.FSM()
    assert list(f.start.bfs()) == [f.start]
    f = fsm.FSM(None)
    assert list(f.start.bfs()) == [f.start]
    f = fsm.FSM('')
    assert list(f.start.bfs()) == [f.start, f.stop]

    assert not fsm_eval(fsm.FSM(None), '')
    assert not fsm_eval(fsm.FSM(None), '-')
    assert fsm_eval(fsm.FSM(''), '')
    assert not fsm_eval(fsm.FSM(''), '-')
    assert not fsm_eval(fsm.FSM('-'), '')
    assert fsm_eval(fsm.FSM('-'), '-')

    assert fsm_eval(fsm.FSM('-') + fsm.FSM('+'), '-')
    assert fsm_eval(fsm.FSM('-') + fsm.FSM('+'), '+')
    assert not fsm_eval(fsm.FSM('-') + fsm.FSM('+'), '')
    assert not fsm_eval(fsm.FSM('-') + fsm.FSM('+'), '+-')
    assert not fsm_eval(fsm.FSM('-') + fsm.FSM('+'), '-+')

    assert not fsm_eval(fsm.FSM('-') * fsm.FSM('+'), '-')
    assert not fsm_eval(fsm.FSM('-') * fsm.FSM('+'), '+')
    assert not fsm_eval(fsm.FSM('-') * fsm.FSM('+'), '')
    assert not fsm_eval(fsm.FSM('-') * fsm.FSM('+'), '+-')
    assert fsm_eval(fsm.FSM('-') * fsm.FSM('+'), '-+')

    assert fsm_eval(fsm.FSM('-') ** None, '')
    assert fsm_eval(fsm.FSM('-') ** None, '-')
    assert fsm_eval(fsm.FSM('-') ** None, '--')
    assert not fsm_eval(fsm.FSM('-') ** None, '+')
    assert not fsm_eval(fsm.FSM('-') ** None, '-+')
    assert not fsm_eval(fsm.FSM('-') ** None, '+-')

def test_dimple():
    assert repr(fsm.FSM('-') * fsm.FSM('+')) == '1\n\n2\n\n1 3 -\n3 4 \n4 2 +\n'

def check_fsm_no_eps(a: fsm.FSM):
    for n in a.start.bfs():
        assert '' not in n.next or n.next[''] == []


def check_fsm_is_det(a: fsm.FSM):
    for n in a.start.bfs():
        assert '' not in n.next or n.next[''] == []
        assert all([len(nl) < 2 for nl in n.next.values()])


def check_fsm_is_full(a: fsm.FSM, labels: str):
    for n in a.start.bfs():
        assert '' not in n.next or n.next[''] == []
        assert all([len(nl) < 2 for nl in n.next.values()])
        assert all([len(n.next[l]) == 1 for l in labels])


def check_equal(a: fsm.FSM, s: fsm.FSM):
    a_to_s: dict[fsm.Node, fsm.Node] = {
        d: f for d, f in zip(a.start.bfs(), s.start.bfs())}
    s_to_a: dict[fsm.Node, fsm.Node] = {
        d: f for d, f in zip(s.start.bfs(), a.start.bfs())}
    assert len(list(a.start.bfs())) == len(
        list(s.start.bfs())) == len(a_to_s) == len(s_to_a)
    assert [*a.start.bfs()] == [*a_to_s.keys()] == [*s_to_a.values()]
    assert [*s.start.bfs()] == [*s_to_a.keys()] == [*a_to_s.values()]

    def check_a_to_s(a_to_s, s_to_a):
        for d, f in a_to_s.items():
            assert a_to_s[d] == f
            for l in d.next:
                assert {a_to_s[n] for n in d.next[l]} == set(f.next[l])
    check_a_to_s(a_to_s, s_to_a)
    check_a_to_s(s_to_a, a_to_s)


seed = 881390418032792034
# seed = random.randint(0, 1<<64-1)
print(f'{seed = }')
rand = random.Random(seed)

@pytest.mark.parametrize('arg', range(99))
def test_fsm_stress(arg):
    labels = 'qwertyuiop'
    r = random_fsm(rand, 8, labels)
    if r[1] is not None:
        a = s = d = f = g = h = 0
        try:
            z = convert.reg_to_ast(r[4])
            a = convert.ast_to_eps_non_det_fsm(z)
            s = convert.eps_non_det_fsm_to_non_det_fsm(a)
            check_fsm_no_eps(s)
            d = convert.non_det_fsm_to_det_fsm(s)
            check_fsm_is_det(d)
            f = convert.det_fsm_to_full_det_fsm(d, labels)
            check_fsm_is_full(f, labels)
            g = convert.full_fsm_to_min_full_fsm(f)
            check_fsm_is_full(g, labels)
            h = convert.full_fsm_to_min_full_fsm(g)
            check_fsm_is_full(h, labels)
            check_equal(g, h)
        except RecursionError:
            for var in [a, s, d, f, g, h]:
                if var != 0:
                    print(graphviz(var))
                    break
            raise IndentationError

        try:
            assert fsm_eval(r[0], r[1])
            assert fsm_eval(a, r[1])
            assert fsm_eval(s, r[1])
            assert fsm_eval(d, r[1])
            assert fsm_eval(f, r[1])
            assert fsm_eval(g, r[1])
            assert fsm_eval(h, r[1])
            assert re.fullmatch(r[2], r[1])
            for t in r[3]:
                if t is not None:
                    u = bool(re.fullmatch(r[2], t))
                    assert fsm_eval(r[0], t) == u
                    assert fsm_eval(a, t) == u
                    assert fsm_eval(s, t) == u
                    assert fsm_eval(d, t) == u
                    assert fsm_eval(f, t) == u
                    assert fsm_eval(g, t) == u
                    assert fsm_eval(h, t) == u
        except TabError:
            pass

@pytest.mark.parametrize('arg', range(99))
def test_fsm_speed(arg):
    labels = 'qwertyuiop'
    try:
        r = random_fsm(rand, 10, labels)
    except RecursionError:
        return
    if r[1] is not None:
        a = s = d = f = g = h = 0
        try:
            z = convert.reg_to_ast(r[4])
            a = convert.ast_to_eps_non_det_fsm(z)
            s = convert.eps_non_det_fsm_to_non_det_fsm(a)
            check_fsm_no_eps(s)
            d = convert.non_det_fsm_to_det_fsm(s)
            check_fsm_is_det(d)
            f = convert.det_fsm_to_full_det_fsm(d, labels)
            check_fsm_is_full(f, labels)
            g = convert.full_fsm_to_min_full_fsm(f)
            check_fsm_is_full(g, labels)
            h = convert.full_fsm_to_min_full_fsm(g)
            check_fsm_is_full(h, labels)
            check_equal(g, h)
        except RecursionError:
            for var in [a, s, d, f, g, h]:
                if var != 0:
                    print(graphviz(var))
                    break
            raise IndentationError

        try:
            assert fsm_eval(h, r[1])
            assert re.fullmatch(r[2], r[1])
            for t in r[3]:
                if t is not None:
                    u = bool(re.fullmatch(r[2], t))
                    assert fsm_eval(h, t) == u
        except TabError:
            pass

