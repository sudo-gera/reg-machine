import typing
import ast
from copy import deepcopy as cp
from collections import defaultdict as dd

import fa


def fa_has_eps(a: fa.FA) -> bool:
    for node in a.start.bfs():
        if node.next_nodes_by_label.get('', set()):
            return True
    return False

def fa_has_no_eps(a: fa.FA) -> bool:
    return not fa_has_eps(a)


def fa_is_det(a: fa.FA) -> bool:
    if fa_has_eps(a):
        return False
    for node in a.start.bfs():
        for next_nodes_by_label in node.next_nodes_by_label.values():
            if len(next_nodes_by_label) > 1:
                return False
    return True


def fa_is_full(a: fa.FA, labels: str) -> bool:
    if not fa_is_det(a):
        return False
    for node in a.start.bfs():
        for label in labels:
            if len(node.next_nodes_by_label[label]) != 1:
                return False
    return True
