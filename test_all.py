from __future__ import annotations
from copy import deepcopy as cp
import random
import re
from collections import defaultdict as dd
import time
import ast
import sys
import io
import pytest

import fsm
import convert
import command


def fsm_eval(a: fsm.FSM, path: str, limit=64):
    ops = 0
    eps_map = {n: list(n.bfs(True)) for n in a.start.bfs()}
    current_nodes = list(a.start.bfs(True))
    next_nodes: dict[fsm.Node, None] = {}
    for c in path:
        for n in current_nodes:
            for nn in n.next[c]:
                next_nodes |= dict.fromkeys(eps_map[nn])
                ops += 1
                if ops > limit:
                    raise TabError
        current_nodes = list(next_nodes)
        next_nodes = {}
    res = any([n.stop or a.stop == n for n in current_nodes])
    return res


def random_fsm(rand: random.Random,
               depth,
               labels  # allowed letters
               ) -> tuple[fsm.FSM,
                          str | None,  # random string that matches
                          str | None,  # regex for re.fullmatch
                          list[str | None],  # random strings that maybe match
                          str | None]:  # regex for converting to FSM
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
        res += f'    {id_map[n]} [ label = "{id_map[n]} {n.stop or n == a.stop}" ]\n'
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
    f = fsm.FSM('-')
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


def test_io():
    assert (fsm.FSM('-') * fsm.FSM('+')
            ).dimple() == '1\n\n4\n\n1 2 -\n2 3 \n3 4 +\n'
    check_equal(fsm.FSM('-') * fsm.FSM('+'),
                fsm.FSM.from_dimple('1\n\n2\n\n1 3 -\n3 4 \n4 2 +\n'))

    def test_main(argv, text_in, text_out, code):
        stdin = io.StringIO()
        stdin.write(text_in)
        stdin.seek(0)
        stdout = io.StringIO()
        assert code == command.main(argv, stdin, stdout)
        stdout.seek(0)
        assert stdout.read() == text_out
    test_main(
        ['command.py'],
        '',
        'usage: command.py <input format> <output format> [<labels>]\n',
        1)
    test_main(['command.py', 'reg', 'reg'], '0\n', '0\n', 0)
    test_main(
        [
            'command.py',
            'reg',
            'peg'],
        '',
        'unknown format: peg.\nsupported formats are:\n    reg\n    eps-non-det-fsm\n    non-det-fsm\n    det-fsm\n    full-det-fsm\n    min-full-det-fsm\n    invert-full-det-fsm\n',
        1)
    test_main(['command.py', 'det-fsm', 'reg'], '',
              'this conversion order is not supported.\n', 1)
    test_main(['command.py', 'reg', 'det-fsm'], '0', '\n1\n\n\n', 0)
    test_main(['command.py', 'reg', 'full-det-fsm'],
              '0', 'labels argument is undefined.\n', 1)
    test_main(['command.py',
               'non-det-fsm',
               'min-full-det-fsm',
               'ab'],
              '0\n\n3\n\n0 3 a\n3 3 a\n3 3 b\n0 1 b\n2 3 a\n2 1 b\n1 2 b\n1 1 a\n',
              '\n1\n\n2\n\n1 2 a\n1 3 b\n2 2 a\n2 2 b\n3 1 b\n3 3 a\n',
              0)
    test_main(['command.py', 'reg', 'det-fsm'],
              '', 'Incorrect input data.\n', 1)


seed = 3099010176601051186
# seed = random.randint(0, 1 << 64 - 1)
print(f'{seed = }')
rand = random.Random(seed)
# print(f'{seed = }', file=open('/dev/tty', 'w'))

import task6

def test_task6():
    check = task6.check
    assert     check('',  'a', 0)
    assert not check('',  'a', 1)
    assert     check('a', 'a', 0)
    assert     check('a', 'a', 1)
    assert not check('a', 'a', 2)
    assert     check('a', 'b', 0)
    assert not check('a', 'b', 1)
    assert     check('aa+', 'a', 0)
    assert     check('aa+', 'a', 1)
    assert not check('aa+', 'a', 2)
    assert     check('aa+', 'b', 0)
    assert not check('aa+', 'b', 1)
    assert     check('ab+', 'a', 0)
    assert     check('ab+', 'a', 1)
    assert not check('ab+', 'a', 2)
    assert     check('ab+', 'b', 0)
    assert     check('ab+', 'b', 1)
    assert not check('ab+', 'b', 2)
    assert     check('aa.', 'a', 0)
    assert     check('aa.', 'a', 1)
    assert     check('aa.', 'a', 2)
    assert not check('aa.', 'a', 3)
    assert     check('ab.', 'a', 0)
    assert     check('ab.', 'a', 1)
    assert not check('ab.', 'a', 2)
    assert     check('ab + c.aba. * .bac. + . + *', 'a', 2)
    assert not check('acb..bab.c. * .ab.ba. + . + *a.', 'b', 3)
    try:
        check('aa', 'a', 0)
        assert 0
    except Exception:
        pass
    try:
        check('a.', 'a', 0)
        assert 0
    except Exception:
        pass

def test_task6_more():
    check = task6.check
    assert not check('bac.1*+b1+b1+.*ca.1.c.1.b+..*+1+', 'c', 2)
    assert     check('cccb.1++111a.a+.1*+.+*a.*+11+.1.', 'c', 4)
    assert     check('bb+*c.*c.cbb+*c*bbb+..b+aa...*..', 'a', 0)
    assert     check('aca1*.c1..+1a*.ab.*1.c.b.a*+*+.+', 'c', 1)
    assert not check('1b.aca.b.+a*1aba...c+1.+a.1.1++.', 'b', 2)
    assert     check('c11a*1++c11.++b+.a1..b..a*ab+*+.', 'c', 1)
    assert     check('bcb*c+*cbc++c..+bb1*..+c..c.a+a.', 'a', 1)
    assert     check('11bbc+.b.+*+*ca*.1+b*a+c*+cc.+..', 'c', 2)
    assert not check('1bcba.1.b+.a.+1ccbcb.b..+++c..*.', 'b', 4)
    assert not check('acbba+1bc.1*++..*+cb1..c1*+c.+..', 'a', 2)
    assert not check('acab.c***11*a.+b.b.+.b..bc*+b+.+', 'c', 2)
    assert not check('1abbaabc*a*a1..+..++..bb.b*++c+.', 'a', 5)
    assert     check('b*ba++b1.aa.c*+c.*+c1*+.+aba.+*+', 'c', 2)
    assert not check('bbca1a+11+*a.cc.11.+++a.+b+.++1+', 'b', 2)
    assert     check('ab1a*b++++*cc*+1+ca*++*b+1**.*+*', 'b', 0)
    assert     check('11c+ac+.cbc*++cc.+c..bcb*+..*1++', 'a', 1)
    assert not check('cacb+1+b+c11.1*+.1*+*+ca*c.*.++.', 'b', 5)
    assert not check('bba+*c+*.a11..a1*bc.++.+b+b1*.*+', 'a', 4)
    assert not check('11c.+cb++11b.c.1aa.*1++...1ba++.', 'b', 3)
    assert not check('b1baca+.ac.a+.c+1a1..b*+.*.+*.1+', 'a', 4)
    assert     check('aac.1+c*+1+1a.c*+.+*bc++b+cc1+.+', 'c', 2)
    assert     check('1*b+***ac***.c.1+*cb.+a**.*.b.c.', 'b', 1)
    assert     check('1c.1*baa1+..+aa+a.bb.*.*+1++c+b.', 'b', 0)
    assert not check('a1a.ac++*b+b*c*+c++c+.cc+1..a1+.', 'c', 2)
    assert     check('1c1b11+c.1b..c+b.++*+bc..*.a+*a+', 'c', 0)
    assert not check('ca.aab+b1c.+b.c.1*+*1*b++.c..b..', 'a', 3)
    assert not check('bcc.*+1*1c+.*b+111*c.+.+a.1b..*.', 'a', 4)
    assert     check('b1.cac.ba.+1+*a+cc*.bb+*..1+..c.', 'c', 0)
    assert     check('11*1*..cb*c.1a.+.*1a+*b+c+c+a.+.', 'b', 0)
    assert     check('bbca+aac.caa1*b..+....1+b.1.++1+', 'a', 2)
    assert not check('cc+b+bc1a1a*c+*+*+*a+.a.c+*c++++', 'b', 3)
    assert not check('c*bc.aba.cb1*+b+c1.+.....a1+.*c.', 'b', 2)
    assert     check('1b*.c.bb1b+abbb.b.+a+.++.1c+.c+.', 'c', 2)
    assert not check('1*c.ca1b**a*.*1+a*..a+1.+a.a*.+.', 'c', 3)
    assert     check('cab.*ab+*1+*.+b+aa1*+.*b1++a*++*', 'b', 1)
    assert     check('1c.b*b1.c*.*.aa.*+*1ab+..a.a++1.', 'a', 5)
    assert not check('bc.c1a+aabc1.+*+*.b+a+.c1+++*.b+', 'a', 1)
    assert not check('ca1.aca*.1*.b.1..c.b*a.+.bac+...', 'c', 2)
    assert     check('cb1+.cab+*.cb1a*++c.+a.a...cc+.*', 'c', 0)
    assert not check('1cba.*++*ba1.+c.c**.*bcb.*.+*.**', 'a', 2)
    assert not check('aa*b1.*c.++a.1b.aa.+*11.*..bb.*.', 'c', 3)
    assert     check('ab1*aa1..+ba..+*a+.1a.b.1*a.b+++', 'a', 3)
    assert     check('11cb+*a*+ac1.*++.*.*cb++aa.1.*.*', 'b', 2)
    assert     check('1bc.a+bb.cb++++111cb+.+*1+1+.1++', 'b', 0)
    assert not check('bcc..c.c1+.a+bc.a+.b.ba1cb.+.*+.', 'b', 2)
    assert     check('11aaa..1ccaa.+.+*.+c1.*c.+a.1.*.', 'a', 1)
    assert not check('bba*a+*+1+aa++11.1a.ab.+ac..*+++', 'b', 2)
    assert not check('abc*ac..c1a*1b.a+*+..b..a.+1+a+.', 'a', 5)
    assert     check('acaa.11.cbca1a.*+b..*++...1c*.+.', 'b', 0)
    assert     check('b1a.cb+c+a*++ab+a..+a1aa.a+c...+', 'b', 2)
    assert     check('b1b++*1*1c*.a.*+c1.*+bbc+..b+c.+', 'b', 0)
    assert not check('11.1*a*a.c1.+a.1..b*a*...11+c+*+', 'b', 5)
    assert     check('bac.1*.a+a+c*b.+c+*bb*b+..b*a.++', 'c', 0)
    assert     check('ab*b*a*+.*c++b+b+*bbaa...b..*1+*', 'c', 5)
    assert     check('cb1a+.c+a*+.1.a.1.a1a.a1*.+++*c.', 'c', 0)
    assert not check('ac*b+*.1*.a1cb1+bb*+a.++cc....*+', 'b', 3)
    assert not check('b*c1+a+.cbb*a1ccb.*1.*+..c.*...+', 'c', 4)
    assert not check('a*c.bc+a+cca.+c1a.1++b.a+.a..+a+', 'b', 4)
    assert not check('c1c.caacc..b.+aa.+++c+11+c*+++b.', 'b', 3)
    assert not check('ba1b1c.*+a.+*c*.*+*c.*bcc....b.*', 'c', 5)
    assert not check('c***abcb.1+a1+.bb.*bc.....a.*.a+', 'a', 5)
    assert     check('a1+bc1a*+*a.ac++.c+ccac+1*...+.+', 'b', 1)
    assert not check('1*a.*c+ca+1*a..+a*+a+a.cb.1..1+*', 'c', 5)
    assert     check('bc*.a1b.1+cab.ab1++.bb+.+a++a.+.', 'b', 0)
    assert     check('aaba..*acb*a*+a+*.++.*b.c+a11++.', 'a', 1)
    assert not check('c*1+bbb..a1+.ac.+*ca.b*.c+.*+c*.', 'a', 2)
    assert not check('bab..bb.+1ba+c1.*++aac1+++1b.+.+', 'a', 5)
    assert     check('bca1b*.*+c.cb.+c.1c++c..*b+c*+*.', 'b', 3)
    assert not check('a*ca*ca11+*+.a.b..*++1*+b*b*+b+.', 'c', 4)
    assert     check('bbbac.c*b+aac+*.+a+.c.*++b+*.a+*', 'a', 2)
    assert     check('bc1*.bac+..ac+*+c*ca..b*c.*.1+++', 'b', 1)
    assert not check('cb+a1cac.1*c1..*.acc.*1.+*+..+*+', 'b', 2)
    assert not check('ac1*1.+cc+*bb+1a.+1ac+.+.1+.+b*.', 'a', 3)
    assert not check('cb1**.a1.ac*c.**.11*...++c*+a.a+', 'b', 3)
    assert     check('c1aaa*+.a.+a*c.*1cacb++.a.++b..+', 'b', 0)
    assert not check('ccca++b.a.b++a*c*a.*1.c.c+a.+c+.', 'b', 5)
    assert not check('11c*.*bbca1*+.1b*ca..***+a+..+..', 'b', 2)
    assert     check('bb1+aa.+cc.*c+a.1.bb*b+*a+..1+++', 'c', 2)
    assert     check('111+cb*b1.*b*ac+a++*+c+*..a.c...', 'c', 1)
    assert not check('111b+ca.++ab*..a+a*1+b.c+b1.*++.', 'c', 5)
    assert not check('bcc*1*c..1.*a*+b.+ab+.1+ca.*1+++', 'b', 5)
    assert     check('baac*..1*b+1.*.1+*ab.*1c+b+c++..', 'b', 2)
    assert     check('111*b++baa+*c+.*c.1.c*.ab..*..c.', 'c', 1)
    assert     check('11b..c*abcbc.+.+b+acca..ca...+++', 'c', 4)
    assert     check('b11*.cc+++11c+c*c.1+b..*.+*b*a+.', 'a', 0)
    assert not check('b11b.1aa.ac.+++ba*ca+*a.+...+c*.', 'b', 5)
    assert     check('ac1baa.*1b.a*+....+a.a+*b+*1.c+*', 'a', 3)
    assert     check('cc1*..*bb.1*++1.cbc..ccca..+..c.', 'b', 2)
    assert     check('bcbab.+1.ba..a+11*11*++..+1++1*+', 'b', 0)
    assert     check('bca.11b111.*.c+b.a++c.+*11*+++.+', 'c', 0)
    assert not check('ca1++bb*a1b*+c*.1*.*+1.+c..+1.1.', 'a', 5)
    assert not check('ac.*b1aa*.cba*c++.b.1+.+.aa.c.++', 'a', 3)
    assert     check('1b*a*1.bc+ca.*b+.+a*ab+.1.b..+*+', 'c', 1)
    assert not check('b1a*a+..c.11c.*.*aa1.c++a+aa...+', 'b', 3)
    assert     check('1*b1b+*.ca+ba+...c+b.c+a*ca1.++.', 'b', 4)
    assert     check('1caac+11+.1.1+..acbc..+..b*.a+a.', 'c', 0)
    assert     check('11b+bb*b..1.1.c.*.1.*a.*.c+a*.1.', 'b', 4)
    assert not check('1ca+c+*+11a1*+a..bc.c+c+.*b++1.+', 'b', 3)
    assert not check('a*1*+cc..b+1a.1c.b1+c+*+*.+b+1*+', 'b', 3)
    assert     check('ba1a+b+.1.1*.abb1+b+++1*a+..+*c.', 'b', 4)
    assert     check('b1+aca1.+.+bb.a1++bc+1ba..*a....', 'b', 5)
    assert     check('ba1a+*++11*.+a1b*...b+*b1b++*c++', 'c', 0)
    assert not check('ba1+c++acc1a.b.*c*..*.c*b.+1...*', 'c', 3)
    assert not check('1b*+1*+1.c+b*.c+a1*.1a1+*++c.c++', 'c', 4)
    assert not check('c1+aac+baa*c.*+cc+*.+*..+b+a.*c+', 'c', 5)
    assert     check('baa*1**c*++.*1a.*c*a*+.b.+*b++1+', 'a', 4)
    assert     check('1*bc.a*+ca1*c1*c1*.+++c.+.+c++b+', 'b', 0)
    assert     check('aac*cab*+.+.1a*.b*1+1*+c.1....b+', 'a', 2)
    assert     check('abb*a+*111+1.+.*+b+b+*+a1b1*.+.+', 'a', 4)
    assert     check('bac.1+1+.bca*1.11cc1.*+..+1+*...', 'b', 0)
    assert not check('cb11+*a+c..a*1.cb+1+.c.a+a..*a++', 'b', 2)
    assert     check('b*bc1+*+ccac*+a.b*c.*1+...a+.+a.', 'a', 2)
    assert not check('b1b1*+b.1+1a+.*+*1a*+cac+*1.+...', 'c', 4)
    assert     check('b1cc1+1*.1+a1.a+.a+ac++bb+.+c.++', 'b', 0)
    assert     check('cabb*..*cb.+a+cbcb1.a..+..1+b*.+', 'c', 1)
    assert     check('1b+1bca..*.11.*cb..a+.c++*a.c.c.', 'c', 0)
    assert not check('1c+c1b+ac++bb1cb11+.++c++*..+a+.', 'c', 3)
    assert not check('11a.+1bb1..1cb1+c*+..b+.1+.1+a..', 'a', 3)
    assert     check('aac*c1b.++*+b.*b*a.+1+.a.*ca++b.', 'b', 1)
    assert not check('acc++a*a*ac+c*+..*a1*..+cb+.b+a+', 'b', 4)
    assert not check('c*ba+1b.+a.b.a.a++ccac.1.a+a+..+', 'b', 5)
    assert     check('ab+1+ccca1..c+1c*++c.*+.c+.1.1.*', 'b', 1)
    assert not check('aaca+a+acb..111*a.+b*+.b*.+.+a.+', 'c', 2)
    assert not check('baa1.b+.bcbcc*+b.*b++b*...cc+...', 'b', 2)
    assert     check('1b.1*cb.b.c.+b1.+1.abb..++1.ac.+', 'b', 0)
    assert not check('bc1b*cb*++1aa...+.*c1+cca.+b.+++', 'b', 4)
    assert not check('cbbbc.a*b..a*+a.b.c+1...*1+.b+c.', 'c', 5)
    assert not check('ab1ba.+c+a.1+c+ac..+*aa+*1.*1...', 'c', 5)
    assert not check('aaca.b.+c+.c.bc.aab++ccb.+.+1+*+', 'a', 3)
    assert     check('b11aab+bb..a.+b..+1.a..c.a+a*.c+', 'b', 4)
    assert     check('aa1+a1b++.a*+a+c.11.ba++.1.1.+c.', 'a', 2)
    assert not check('ab1abbb+b+c+.a+.1cbb+++*.++.a+b+', 'b', 3)
    assert not check('caa+a1b.a..1*++ab.+1+1+c.c1..+a.', 'c', 4)
    assert     check('cc.b*b1++b+c.c*.b1*..+1b11+.++a+', 'a', 1)
    assert     check('cac.*.c*+bba*+b1.+c.ab.cc+..1+..', 'b', 0)
    assert not check('b*c.1*b1.1bc.+cb+*b+a1++.*.++b.*', 'c', 5)
    assert     check('1*c*.ac*+c1..1b+babb*+++ab..*+.+', 'a', 1)
    assert     check('b1a*+1b.1.11.*1++ccb*+..cb..b++.', 'b', 0)
    assert     check('acc+*1a+a*1...c*b*a++bc+*.++ab++', 'b', 5)
    assert not check('cb*a..b.*1a.+b+c1b+b*..b.b..cb++', 'b', 5)
    assert not check('b11*acb*...+a.*b*a+b..a+1.+cb.*+', 'c', 5)
    assert not check('bb1+a*+b.bc1a.b+a+b+..+a+.c.1.c+', 'b', 4)
    assert     check('c*a1a*.b.*+abc++1*+1c+++c+*.1*.*', 'c', 1)
    assert not check('ab1*b*b.b++1c*aa+a+.a..1+c..b++.', 'a', 4)
    assert     check('ba*c+1+.cabc...1b++1..b1.+1c.b++', 'c', 1)
    assert not check('a1caaaa11++*+c.b..a.c.c+*b.+.*..', 'b', 4)

@pytest.mark.parametrize('arg', range(-99, 99))
def test_task6_stress(arg):
    parse = task6.parse
    check = task6.check
    match_longest = task6.match_longest
    while 1:
        try:
            al = 'abc1.+*'
            a = ''.join([rand.choice(al) for q in range(rand.randint(32,32))])
            if '**' in a:
                if rand.randint(0, 7):
                    raise TabError
            try:
                s = parse(a)
            except Exception:
                raise TabError
            l = rand.choice(al[:-4])
            k = rand.randint(0, 5)
            g = match_longest(s, l)
            if g[1] in [0, float('inf')]:
                if rand.randint(0, 7):
                    raise TabError
            res = check(a, l, k)
            z = convert.ast_to_eps_non_det_fsm(s)
            x = convert.eps_non_det_fsm_to_non_det_fsm(z)
            c = convert.non_det_fsm_to_det_fsm(x)
            v = convert.det_fsm_to_full_det_fsm(c, al[:-4])
            b = convert.full_fsm_to_min_full_fsm(v)

            fsm_res = False
            d = b.start
            for c in l*k:
                if not d.next[c]:
                    break
                d = list(d.next[c])[0]
            else:
                for n in d.bfs():
                    fsm_res |= n.stop
            assert res == fsm_res
            break
        except TabError:
            continue



@pytest.mark.parametrize('arg', range(-99, 99))
def test_fsm_stress(arg):
    labels = 'qwertyuiop'
    while True:
        try:
            try:
                r = random_fsm(rand, 8 if arg < 0 else 10, labels)
            except RecursionError:
                raise TabError
            a = s = d = f = g = h = j = k = l = 0
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
                j = convert.invert_full_fsm(f)
                check_fsm_is_full(j, labels)
                k = convert.invert_full_fsm(g)
                check_fsm_is_full(k, labels)
                l = convert.invert_full_fsm(h)
                check_fsm_is_full(l, labels)
                check_equal(k, l)
            except RecursionError:
                for var in [a, s, d, f, g, h, j, k, l][::-1]:
                    if var != 0:
                        print(graphviz(var))
                        break
                raise
            if r[1] is None:
                raise TabError
            assert r[1] is not None

            if arg < 0:
                assert fsm_eval(r[0], r[1])
                assert fsm_eval(a, r[1])
                assert fsm_eval(s, r[1])
                assert fsm_eval(d, r[1])
                assert fsm_eval(f, r[1])
                assert fsm_eval(g, r[1])
            assert fsm_eval(h, r[1])
            if arg < 0:
                assert not fsm_eval(j, r[1])
                assert not fsm_eval(k, r[1])
                assert not fsm_eval(l, r[1])
            assert re.fullmatch(r[2], r[1])
            for t in r[3]:
                if t is not None:
                    u = fsm_eval(h, t)
                    assert u == bool(re.fullmatch(r[2], t))
                    if arg < 0:
                        assert fsm_eval(r[0], t) == u
                        assert fsm_eval(a, t) == u
                        assert fsm_eval(s, t) == u
                        assert fsm_eval(d, t) == u
                        assert fsm_eval(f, t) == u
                        assert fsm_eval(g, t) == u
                        assert fsm_eval(h, t) == u
                        assert fsm_eval(j, t) != u
                        assert fsm_eval(k, t) != u
                        assert fsm_eval(l, t) != u
            break
        except TabError:
            continue
