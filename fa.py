from __future__ import annotations
from copy import deepcopy as cp
import operator
import functools
import collections
from collections import defaultdict as dd
import typing
import io


class Node:

    def __init__(self: Node) -> None:
        self.next_nodes_by_label: dd[str, set[Node]] = dd(set)
        self.is_final: bool = False

    def __rshift__(self: Node, label: str) -> tuple[Node, str]:
        return (self, label)

    def __rrshift__(self: Node, left_label: tuple[Node, str]) -> None:
        left, label, right = left_label + (self, )
        left.next_nodes_by_label[label] |= {right}

    def __hash__(self: Node) -> int:
        return id(self)

    def bfs(self: Node,
            eps_only: bool = False) -> typing.Generator[Node, None, None]:
        q: collections.deque[Node] = collections.deque()
        q.append(self)
        visited = set()
        while id(n := q.popleft()) if q else 0:
            if n not in visited:
                visited.add(n)
                yield n
                for l in [n.next_nodes_by_label, ['']][eps_only]:
                    q.extend(n.next_nodes_by_label[l])


class FA:

    def __deepcopy__(self: FA, memo: dict[int, typing.Any]) -> FA:
        s = FA()
        memo[id(self)] = s
        old_to_new: dd[Node, Node] = dd(Node)
        new_to_old: dict[Node, Node] = {}
        old_to_new[self.start] = s.start
        new_to_old[s.start] = self.start
        for new_n in s.start.bfs():
            old_n = new_to_old[new_n]
            new_n.is_final = old_n.is_final
            if old_n == self.stop:
                s.stop = new_n
            memo[id(new_n)] = old_n
            for l, nl in old_n.next_nodes_by_label.items():
                for old_nn in nl:
                    new_nn = old_to_new[old_nn]
                    new_to_old[new_nn] = old_nn
                    new_n >> l >> new_nn
        return s

    def __init__(self, _value: str | None | ellipsis = ...):
        self.start: Node = Node()
        self.stop: Node = Node()
        value = [_value] if _value is not ... else []
        if value and isinstance(value[0], str):
            self.start >> value[0] >> self.stop

    def __add__(self: FA, other: FA) -> FA:
        self.start >> '' >> other.start
        other.stop >> '' >> self.stop
        return self

    def __mul__(self: FA, other: FA) -> FA:
        self.stop >> '' >> other.start
        self.stop = other.stop
        return self

    def __pow__(self: FA, other: int | None) -> FA:
        if other is None:
            self.stop >> '' >> self.start
            return FA('') + self
        return functools.reduce(operator.mul,
                                map(lambda x: cp(x), [self] * other), FA(''))

    def dimple(self: FA) -> str:
        id_map: dd[Node, int] = dd(lambda: len(id_map) + 1)
        res = io.StringIO()
        print(id_map[self.start], file=res)
        print(file=res)
        for n in self.start.bfs():
            id_map[n]
            if n.is_final or n == self.stop:
                print(id_map[n], file=res)
        print(file=res)
        for n in self.start.bfs():
            for label, nl in n.next_nodes_by_label.items():
                for nn in nl:
                    print(id_map[n], id_map[nn], label, file=res)
        res.seek(0)
        return res.read()

    @staticmethod
    def from_dimple(text_str: str) -> FA:

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
