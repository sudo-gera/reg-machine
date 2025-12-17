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


def fsm_to_dimple(fa: FA) -> str:
    id_map: dd[Node, int] = dd(lambda: len(id_map) + 1)
    res = io.StringIO()
    print(id_map[fa.start], file=res)
    print(file=res)
    for n in fa.start.bfs():
        id_map[n]
        if n.is_final or n == fa.the_only_final_if_exists_or_unrelated_node:
            print(id_map[n], file=res)
    print(file=res)
    for n in fa.start.bfs():
        for label, nl in n.next_nodes_by_label.items():
            for nn in nl:
                print(id_map[n], id_map[nn], label, file=res)
    res.seek(0)
    return res.read()


def dimple_to_fsm(text_str: str) -> FA:

    def index_or_len(a: list[typing.Any], v: typing.Any) -> int:
        if v in a:
            return a.index(v)
        return len(a)

    text = [line.split() for line in text_str.strip().splitlines()]
    start = text[:index_or_len(text, [])]
    text = text[len(start) + 1:]
    stop = text[:index_or_len(text, [])]
    text = text[len(stop) + 1:]
    assert len(start) == 1
    name_to_node: dd[str, Node] = dd(Node)
    res = FA()
    res.start = name_to_node[start[0][0]]
    for line in stop:
        name_to_node[line[0]].is_final = True
    for line in text:
        if len(line) == 2:
            line.append('')
        name_to_node[line[0]] >> line[2] >> name_to_node[line[1]]
    for name, node in name_to_node.items():
        node.name = name
    for node in res.start.bfs():
        assert node.name is not None
    return res


def dimple_to_json(dimple_text: str, _letters: str) -> dict[str, typing.Any]:
    lines = [line.rstrip() for line in dimple_text.splitlines()]

    i = 0
    n = len(lines)

    # 1. стартовое состояние
    if i >= n or lines[i] == "":
        raise ValueError("Отсутствует стартовое состояние")
    start_state = lines[i]
    i += 1

    # 2. пустая строка (если есть)
    if i < n and lines[i] == "":
        i += 1

    # 3. финальные состояния
    final_states = []
    while i < n and lines[i] != "":
        final_states.append(lines[i])
        i += 1

    # 4. пустая строка после финальных (если есть)
    if i < n and lines[i] == "":
        i += 1

    # 5. переходы
    states = {start_state}
    letters = set(_letters)
    transitions = []

    while i < n:
        if lines[i] == "":
            i += 1
            continue

        parts = lines[i].split()
        if len(parts) == 2:
            frm, to = parts
            letter = ""
        elif len(parts) == 3:
            frm, to, letter = parts
            letters.add(letter)
        else:
            raise ValueError(f"Некорректная строка перехода: {lines[i]}")

        states.add(frm)
        states.add(to)
        transitions.append([frm, letter, to])
        i += 1

    return {
        "states": sorted(states),
        "letters": sorted(letters),
        "transition_function": transitions,
        "start_states": [start_state],
        "final_states": final_states
    }


def json_to_dimple(automaton: dict[str, typing.Any]) -> str:
    start_states = automaton["start_states"]
    if len(start_states) != 1:
        raise ValueError("Dimple поддерживает только одно стартовое состояние")

    start_state = start_states[0]
    final_states = automaton["final_states"]
    transitions = automaton["transition_function"]

    lines = []

    # 1. старт
    lines.append(start_state)
    lines.append("")

    # 2. финальные
    for s in final_states:
        lines.append(s)
    lines.append("")

    # 3. переходы
    for frm, letter, to in transitions:
        if letter == "":
            lines.append(f"{frm} {to}")
        else:
            lines.append(f"{frm} {to} {letter}")

    return "\n".join(lines)
