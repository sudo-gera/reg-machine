import typing
import ast
from copy import deepcopy as cp
from collections import defaultdict as dd

import fa


def check_fa_no_eps(a: fa.FA) -> None:
    for n in a.start.bfs():
        assert '' not in n.next_nodes_by_label or n.next_nodes_by_label[
            ''] == set()


def check_fa_is_det(a: fa.FA) -> None:
    for n in a.start.bfs():
        assert '' not in n.next_nodes_by_label or n.next_nodes_by_label[
            ''] == set()
        assert all([len(nl) < 2 for nl in n.next_nodes_by_label.values()])


def check_fa_is_full(a: fa.FA, labels: str) -> None:
    for n in a.start.bfs():
        assert '' not in n.next_nodes_by_label or n.next_nodes_by_label[
            ''] == set()
        assert all([len(nl) < 2 for nl in n.next_nodes_by_label.values()])
        assert all([len(n.next_nodes_by_label[l]) == 1 for l in labels])
