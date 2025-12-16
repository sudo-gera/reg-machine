import typing
import ast
from copy import deepcopy as cp
from collections import defaultdict as dd

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
                if isinstance(a.right.value, int | type(None)):
                    return this(a.left)**a.right.value
    elif isinstance(a, ast.Name):
        return fa.FA(a.id)
    elif isinstance(a, ast.Constant):
        if isinstance(a.value, int):
            return fa.FA([None, ''][a.value])
    assert False


def remove_eps(fa: fa.FA) -> fa.FA:
    fa = cp(fa)
    fa.stop.is_final = True
    for root in fa.start.bfs():
        for node in root.bfs(eps_only=True):
            root.is_final |= node.is_final
            for label, next_nodes in node.next_nodes_by_label.items():
                root.next_nodes_by_label[label] |= next_nodes
    for root in fa.start.bfs():
        if '' in root.next_nodes_by_label:
            del root.next_nodes_by_label['']
    return fa


def make_deterministic(a: fa.FA) -> fa.FA:
    a = cp(a)
    s = fa.FA()
    new_to_old: dd[fa.Node, set[fa.Node]] = dd(set)
    old_to_new: dd[frozenset[fa.Node], fa.Node] = dd(fa.Node)
    new_to_old[s.start] = {a.start}
    for nn in s.start.bfs():
        for n in new_to_old[nn]:
            nn.is_final |= n.is_final
            for l, nl in n.next_nodes_by_label.items():
                nn.next_nodes_by_label[l] |= nl
        for l, nl in nn.next_nodes_by_label.items():
            n = old_to_new[frozenset(nl)]
            nn.next_nodes_by_label[l] = {n}
            new_to_old[n] = set(nl)
    return s


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


def invert_full_fsm(a: fa.FA) -> fa.FA:
    a = cp(a)
    for n in a.start.bfs():
        n.is_final = not n.is_final
    return a
