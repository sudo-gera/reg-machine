import typing
import ast
from copy import deepcopy as cp
from collections import defaultdict as dd

from utils import debug
import fa


def regex_to_ast(a: str) -> ast.AST:
    expr = ast.parse(a).body[0]
    assert isinstance(expr, ast.Expr)
    return expr.value


def ast_to_eps_nfa(a: ast.AST) -> fa.FA:
    this = ast_to_eps_nfa
    if isinstance(a, ast.BinOp):
        if isinstance(a.op, ast.Add):
            return this(a.left) + this(a.right)
        if isinstance(a.op, ast.Mult):
            return this(a.left) * this(a.right)
        if isinstance(a.op, ast.Pow):
            if isinstance(a.right, ast.Constant):
                if isinstance(a.right.value, int):
                    return this(a.left) ** a.right.value
                if a.right.value is None:
                    return ~this(a.left)
    elif isinstance(a, ast.Name):
        return fa.FA(a.id)
    elif isinstance(a, ast.Constant):
        if isinstance(a.value, int):
            return fa.FA([None, ''][a.value])
    assert False


def remove_eps(fa: fa.FA) -> fa.FA:
    fa = cp(fa)
    fa.the_only_final_if_exists_or_unrelated_node.is_final = True
    for root in fa.start.bfs():
        for node in root.bfs(eps_only=True):
            root.is_final |= node.is_final
            for label, next_nodes in node.next_nodes_by_label.items():
                root.next_nodes_by_label[label] |= next_nodes
    for root in fa.start.bfs():
        if '' in root.next_nodes_by_label:
            del root.next_nodes_by_label['']
    return fa


def make_deterministic(old_fa: fa.FA) -> fa.FA:
    old_fa = cp(old_fa)
    new_fa = fa.FA()

    new_to_old: dd[fa.Node, set[fa.Node]] = dd(set)
    old_to_new: dd[frozenset[fa.Node], fa.Node] = dd(fa.Node)

    new_to_old[new_fa.start] = {old_fa.start}

    for new_node in new_fa.start.bfs():

        for old_node in new_to_old[new_node]:

            new_node.is_final |= old_node.is_final

            for label, next_nodes_by_label in old_node.next_nodes_by_label.items():
                new_node.next_nodes_by_label[label] |= next_nodes_by_label

        for label, next_nodes_by_label in new_node.next_nodes_by_label.items():

            old_node = old_to_new[frozenset(next_nodes_by_label)]
            new_node.next_nodes_by_label[label] = {old_node}
            new_to_old[old_node] = set(next_nodes_by_label)

    return new_fa


def make_full(a: fa.FA, labels: str) -> fa.FA:
    a = cp(a)
    new = fa.Node()
    for n in a.start.bfs():
        for l in labels:
            if not n.next_nodes_by_label[l]:
                n >> l >> new
    return a


def make_min(a: fa.FA) -> fa.FA:
    a = cp(a)
    labels: list[str] = list(a.start.next_nodes_by_label)
    old_node_to_group_save: dict[fa.Node, int] = {}
    old_node_to_group: dict[fa.Node, int] = {
        n: int(n.is_final)
        for n in a.start.bfs()
    }
    uniq_nums: dd[tuple[int, ...], int] = dd(lambda: len(uniq_nums))
    while old_node_to_group_save != old_node_to_group:
        uniq_nums.clear()
        old_node_to_group_save = dict(old_node_to_group)
        old_node_to_group.clear()
        for n in a.start.bfs():
            next_groups = [old_node_to_group_save[n]]
            for l in labels:
                for nn in n.next_nodes_by_label[l]:
                    next_groups.append(old_node_to_group_save[nn])
            old_node_to_group[n] = uniq_nums[tuple(next_groups)]
    group_to_old_node = {g: n for n, g in old_node_to_group.items()}
    s = fa.FA()
    group_to_new_node = dd(fa.Node)
    group_to_new_node[old_node_to_group[a.start]] = s.start
    new_node_to_group = {s.start: old_node_to_group[a.start]}
    for new_n in s.start.bfs():
        g = new_node_to_group[new_n]
        old_n = group_to_old_node[g]
        for l, nl in old_n.next_nodes_by_label.items():
            for nn in nl:
                group = old_node_to_group[nn]
                nnn = group_to_new_node[group]
                new_n >> l >> nnn
                new_node_to_group[nnn] = group
    for n, g in old_node_to_group.items():
        group_to_new_node[g].is_final |= n.is_final
    return s


def invert_full_fa(a: fa.FA) -> fa.FA:
    a = cp(a)
    for n in a.start.bfs():
        n.is_final = not a.is_final(n)
    a.the_only_final_if_exists_or_unrelated_node = fa.Node()
    return a

def fa_to_re(a: fa.FA) -> str:
    a = cp(a)

    a = fa.FA() + a

    a.the_only_final_if_exists_or_unrelated_node.is_final = True

    a.the_only_final_if_exists_or_unrelated_node = fa.Node()

    a.the_only_final_if_exists_or_unrelated_node.is_final = True

    # print(f'{a.the_only_final_if_exists_or_unrelated_node = }', file=debug)

    for node in a.start.bfs():
        if node.is_final and node is not a.the_only_final_if_exists_or_unrelated_node:
            node.is_final = False
            node.next_nodes_by_label[''] |= {a.the_only_final_if_exists_or_unrelated_node}
    
    nodes = {*a.start.bfs()}

    if a.the_only_final_if_exists_or_unrelated_node not in nodes:
        return '0'

    assert a.the_only_final_if_exists_or_unrelated_node in nodes

    for node in nodes:
        assert node is a.the_only_final_if_exists_or_unrelated_node and node.is_final or not node.is_final

    # now a.the_only_final_if_exists_or_unrelated_node is indeed the only final and not unrelated

    for node in a.start.bfs():
        for label, next_nodes in node.next_nodes_by_label.items():
            ltext = '1' if label == '' else label
            for next_node in next_nodes:
                if node.regex_by_next_node[next_node] != '0':
                    node.regex_by_next_node[next_node] = f'({node.regex_by_next_node[next_node]}+{ltext})'
                else:
                    node.regex_by_next_node[next_node] = ltext

    # print(f'{a.the_only_final_if_exists_or_unrelated_node = }', file=debug)

    while 1:
        nodes = {*a.start.bfs()}
        # print(nodes, file=debug)
        # for node in nodes:
            # for next_node, re in node.regex_by_next_node.items():
                # print(f'{node} -> {re} -> {next_node}', file=debug)
        
        assert a.start in nodes
        assert a.the_only_final_if_exists_or_unrelated_node in nodes
        assert a.the_only_final_if_exists_or_unrelated_node is not a.start

        assert len(nodes) >= 2

        if len(nodes) == 2:
            break

        for q in nodes - {a.start, a.the_only_final_if_exists_or_unrelated_node}:

            if q.regex_by_next_node[q] == '0':
                loop = '1'
            elif q.regex_by_next_node[q] == '1':
                loop = '1'
            else:
                loop = f'({q.regex_by_next_node[q]}**None)'

            for i in nodes - {q}:
                for j in nodes - {q}:
                    ij = i.regex_by_next_node[j]
                    iq = i.regex_by_next_node[q]
                    qj = q.regex_by_next_node[j]
                    if '0' in [iq, loop, qj]:
                        res = ij
                    elif ij == '0':
                        if iq == loop == '1':
                            res = qj
                        elif iq == qj == '1':
                            res = loop
                        elif loop == qj == '1':
                            res = iq
                        elif iq == '1':
                            res = f'({loop}*{qj})'
                        elif loop == '1':
                            res = f'({iq}*{qj})'
                        elif qj == '1':
                            res = f'({iq}*{loop})'
                        else:
                            res = f'({iq}*{loop}*{qj})'
                    else:
                        if iq == loop == '1':
                            if ij < qj:
                                res = f'({ij}+{qj})'
                            elif ij > qj:
                                res = f'({qj}+{ij})'
                            else:
                                res = f'{qj}'
                        elif iq == qj == '1':
                            if ij < loop:
                                res = f'({ij}+{loop})'
                            elif ij > loop:
                                res = f'({loop}+{ij})'
                            else:
                                res = f'{loop}'
                        elif loop == qj == '1':
                            if ij < iq:
                                res = f'({ij}+{iq})'
                            elif ij > iq:
                                res = f'({iq}+{ij})'
                            else:
                                res = f'{iq}'
                        elif iq == '1':
                            res = f'({ij}+{loop}*{qj})'
                        elif loop == '1':
                            res = f'({ij}+{iq}*{qj})'
                        elif qj == '1':
                            res = f'({ij}+{iq}*{loop})'
                        else:
                            res = f'({ij}+{iq}*{loop}*{qj})'
                    # print(f'{ij = !r} + {iq = !r} * {loop = !r} * {qj = !r} -> {res = !r}', file=debug)
                    i.regex_by_next_node[j] = res
                    # f'({i.regex_by_next_node[j]}+{i.regex_by_next_node[q]}*{loop}*{q.regex_by_next_node[j]})'
                    i.next_nodes_by_label['--'] |= {j}

            for node in nodes - {q}:

                for label, next_nodes in node.next_nodes_by_label.items():
                    next_nodes.discard(q)

                node.regex_by_next_node[q] = '0'

    nodes = {*a.start.bfs()}
    
    assert a.start in nodes
    assert a.the_only_final_if_exists_or_unrelated_node in nodes
    assert a.the_only_final_if_exists_or_unrelated_node is not a.start

    assert len(nodes) == 2

    return a.start.regex_by_next_node[a.the_only_final_if_exists_or_unrelated_node]





