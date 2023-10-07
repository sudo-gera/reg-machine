import fsm
import ast
from copy import deepcopy as cp
from collections import defaultdict as dd


def reg_to_ast(a: str) -> ast.AST:
    expr = ast.parse(a).body[0]
    assert isinstance(expr, ast.Expr)
    return expr.value


def ast_to_eps_non_det_fsm(a: ast.AST) -> fsm.FSM:
    this = ast_to_eps_non_det_fsm
    if isinstance(a, ast.BinOp):
        if isinstance(a.op, ast.Add):
            return this(a.left) + this(a.right)
        if isinstance(a.op, ast.Mult):
            return this(a.left) * this(a.right)
        if isinstance(a.op, ast.Pow):
            if isinstance(a.right, ast.Constant):
                return this(a.left) ** a.right.value
    elif isinstance(a, ast.Name):
        return fsm.FSM(a.id)
    elif isinstance(a, ast.Constant):
        return fsm.FSM([None, ''][a.value])
    assert False


def eps_non_det_fsm_to_non_det_fsm(a: fsm.FSM) -> fsm.FSM:
    a.stop.stop = True
    for root in a.start.bfs():
        for n in root.bfs(True):
            root.stop |= n.stop
            for label, nl in n.next.items():
                root.next[label] |= nl
    for root in a.start.bfs():
        if '' in root.next:
            del root.next['']
    return a


def non_det_fsm_to_det_fsm(a: fsm.FSM) -> fsm.FSM:
    s = fsm.FSM()
    new_to_old: dd[fsm.Node, set[fsm.Node]] = dd(set)
    old_to_new: dd[frozenset[fsm.Node], fsm.Node] = dd(fsm.Node)
    new_to_old[s.start] = {a.start}
    for nn in s.start.bfs():
        for n in new_to_old[nn]:
            nn.stop |= n.stop
            for l, nl in n.next.items():
                nn.next[l] |= nl
        for l, nl in nn.next.items():
            n = old_to_new[frozenset(nl)]
            nn.next[l] = {n}
            new_to_old[n] = set(nl)
    return s


def det_fsm_to_full_det_fsm(a: fsm.FSM, labels: str) -> fsm.FSM:
    new = fsm.Node()
    for n in a.start.bfs():
        for l in labels:
            if not n.next[l]:
                n >> l >> new
    return a


def full_fsm_to_min_full_fsm(a: fsm.FSM):
    labels: list[str] = list(a.start.next)
    old_node_to_group_save: dict[fsm.Node, int] = {}
    old_node_to_group: dict[fsm.Node, int] = {n: int(n.stop) for n in a.start.bfs()}
    uniq_nums: dd[tuple[int, ...], int] = dd(lambda: len(uniq_nums))
    while old_node_to_group_save != old_node_to_group:
        uniq_nums.clear()
        old_node_to_group_save = dict(old_node_to_group)
        old_node_to_group.clear()
        for n in a.start.bfs():
            next_groups = [old_node_to_group_save[n]]
            for l in labels:
                for nn in n.next[l]:
                    next_groups.append(old_node_to_group_save[nn])
            old_node_to_group[n] = uniq_nums[tuple(next_groups)]
    group_to_old_node = {g: n for n, g in old_node_to_group.items()}
    s = fsm.FSM()
    group_to_new_node = dd(fsm.Node)
    group_to_new_node[old_node_to_group[a.start]] = s.start
    new_node_to_group = {s.start : old_node_to_group[a.start]}
    for new_n in s.start.bfs():
        g = new_node_to_group[new_n]
        old_n = group_to_old_node[g]
        for l, nl in old_n.next.items():
            for nn in nl:
                group = old_node_to_group[nn]
                nnn = group_to_new_node[group]
                new_n >> l >> nnn
                new_node_to_group[nnn] = group
    for n, g in old_node_to_group.items():
        group_to_new_node[g].stop |= n.stop
    return s
