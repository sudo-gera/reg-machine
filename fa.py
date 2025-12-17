from __future__ import annotations
from copy import deepcopy as cp
import operator
import functools
import collections
from collections import defaultdict as dd
import typing
import io
from dataclasses import dataclass


class Node:

    def __init__(self: Node) -> None:
        self.next_nodes_by_label: dd[str, set[Node]] = dd(set)
        self.is_final: bool = False
        self.name: str | None = None
        self.regex_by_next_node: dd[Node, str] = dd(lambda: '0')

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(name={self.name!r}, is_final={self.is_final!r})'

    def __rshift__(self: Node, label: str) -> tuple[Node, str]:
        '''
            Creates an edge between nodes by given label.
        '''
        return (self, label)

    def __rrshift__(self: Node, left_label: tuple[Node, str]) -> None:
        '''
            Creates an edge between nodes by given label.
        '''
        left, label, right = left_label + (self, )
        left.next_nodes_by_label[label] |= {right}

    def __hash__(self: Node) -> int:
        return id(self)

    def bfs(
            self: Node,
            eps_only: bool = False
    ) -> typing.Generator[Node, None, None]:
        '''
            This implementation reads next nodes of current node only after it yields it.
        '''

        queue: collections.deque[Node] = collections.deque()
        queue.append(self)

        visited = set()

        while id(node := queue.popleft()) if queue else 0:

            if node not in visited:
                visited.add(node)

                yield node  # Here caller may change next nodes if this node.

                for label in [node.next_nodes_by_label, ['']][eps_only]:
                    queue.extend(node.next_nodes_by_label[label])


class FA:

    def __deepcopy__(old_fa: FA, memo: dict[int, typing.Any]) -> FA:
        '''
            Copy manually via loop to avoid recursion error.
        '''
        new_fa = FA()
        memo[id(old_fa)] = new_fa

        old_to_new: dd[Node, Node] = dd(Node)
        new_to_old: dict[Node, Node] = {}

        old_to_new[old_fa.start] = new_fa.start
        new_to_old[new_fa.start] = old_fa.start

        for new_node in new_fa.start.bfs():

            old_node = new_to_old[new_node]
            new_node.is_final = old_node.is_final
            new_node.name = old_node.name

            if old_node == old_fa.the_only_final_if_exists_or_unrelated_node:
                new_fa.the_only_final_if_exists_or_unrelated_node = new_node

            memo[id(new_node)] = old_node

            for label, old_nodes_next_by_label in old_node.next_nodes_by_label.items():

                for next_old_node in old_nodes_next_by_label:

                    # maybe creates new node
                    next_new_node = old_to_new[next_old_node]

                    new_to_old[next_new_node] = next_old_node

                    new_node >> label >> next_new_node

        return new_fa

    def __init__(self, value: str | None = None):
        '''
            new FA of two nodes, connected by value if value is not None.
        '''

        self.start: Node = Node()
        self.the_only_final_if_exists_or_unrelated_node: Node = Node()

        if value is not None:
            self.start >> value >> self.the_only_final_if_exists_or_unrelated_node

    def __add__(self: FA, other: FA) -> FA:
        '''
            self becomes self + other, other is invalidated.
        '''
        self.start >> '' >> other.start
        other.the_only_final_if_exists_or_unrelated_node >> '' >> self.the_only_final_if_exists_or_unrelated_node
        return self

    def __mul__(self: FA, other: FA) -> FA:
        '''
            self becomes self * other, other is invalidated.
        '''
        self.the_only_final_if_exists_or_unrelated_node >> '' >> other.start
        self.the_only_final_if_exists_or_unrelated_node = other.the_only_final_if_exists_or_unrelated_node
        return self

    def __pow__(self: FA, other: int) -> FA:
        '''
            returns new FA, self is not invalidated.
        '''
        return functools.reduce(operator.mul,
                                map(lambda x: cp(x), [self] * other), FA(''))

    def __invert__(self: FA) -> FA:
        '''
            self ** inf

            Returns new FA, self is invalidated.
        '''
        self.the_only_final_if_exists_or_unrelated_node >> '' >> self.start
        return FA('') + self

    def is_final(self, node: Node) -> bool:
        return node == self.the_only_final_if_exists_or_unrelated_node or node.is_final


def json_to_fa(automaton: dict[str, typing.Any]) -> FA:
    start_states = automaton["start_states"]
    assert len(start_states) == 1

    start_state = start_states[0]
    final_states = set(automaton["final_states"])
    transitions = automaton["transition_function"]

    name_to_node: dd[str, Node] = dd(Node)
    res = FA()

    # start state
    res.start = name_to_node[start_state]

    # final states
    for s in final_states:
        name_to_node[s].is_final = True

    # transitions
    for frm, letter, to in transitions:
        name_to_node[frm] >> letter >> name_to_node[to]

    # assign names
    for name, node in name_to_node.items():
        node.name = name

    # sanity check (same as original)
    for node in res.start.bfs():
        assert node.name is not None

    return res


def fa_to_json(fa: FA, letters: str) -> dict[str, typing.Any]:
    id_map: dd[Node, int] = dd(lambda: len(id_map) + 1)

    start_id = str(id_map[fa.start])

    states: set[str] = {start_id}
    final_states: list[str] = []
    transitions: list[list[str]] = []
    letter_set = set(letters)

    # assign ids and collect states / finals
    for node in fa.start.bfs():
        node_id = str(id_map[node])
        states.add(node_id)

        if fa.is_final(node):
            final_states.append(node_id)

    # collect transitions
    for node in fa.start.bfs():
        node_id = str(id_map[node])
        for label, next_nodes in node.next_nodes_by_label.items():
            for next_node in next_nodes:
                next_node_id = str(id_map[next_node])
                transitions.append([node_id, label, next_node_id])
                if label != "":
                    letter_set.add(label)

    return {
        "states": sorted(states),
        "letters": sorted(letter_set),
        "transition_function": transitions,
        "start_states": [start_id],
        "final_states": final_states,
    }
