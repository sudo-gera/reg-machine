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
        self.next: dd[str, set[Node]] = dd(set)
        self.stop: bool = False

    def __rshift__(self: Node, label: str) -> tuple[Node, str]:
        return (self, label)

    def __rrshift__(self: Node, left_label: tuple[Node, str]) -> None:
        left, label, right = left_label + (self,)
        left.next[label] |= {right}

    def __hash__(self: Node) -> int:
        return id(self)

    def bfs(self: Node,
            eps_only: bool = False) -> typing.Generator[Node,
                                                        None,
                                                        None]:
        q: collections.deque[Node] = collections.deque()
        q.append(self)
        visited = set()
        while id(n := q.popleft()) if q else 0:
            if n not in visited:
                visited.add(n)
                yield n
                for l in [n.next, ['']][eps_only]:
                    q.extend(n.next[l])


class FSM:
    def __deepcopy__(self: FSM, memo: dict[int, typing.Any]):
        s = FSM()
        memo[id(self)] = s
        old_to_new: dd[Node, Node] = dd(Node)
        new_to_old: dict[Node, Node] = {}
        old_to_new[self.start] = s.start
        new_to_old[s.start] = self.start
        for new_n in s.start.bfs():
            old_n = new_to_old[new_n]
            new_n.stop = old_n.stop
            if old_n == self.stop:
                s.stop = new_n
            memo[id(new_n)] = old_n
            for l, nl in old_n.next.items():
                for old_nn in nl:
                    new_nn = old_to_new[old_nn]
                    new_to_old[new_nn] = old_nn
                    new_n >> l >> new_nn
        return s

    def __init__(self, *value: str | None):
        self.start: Node = Node()
        self.stop: Node = Node()
        if value and isinstance(value[0], str):
            self.start >> value[0] >> self.stop

    def __add__(self: FSM, other: FSM) -> FSM:
        self.start >> '' >> other.start
        other.stop >> '' >> self.stop
        return self

    def __mul__(self: FSM, other: FSM) -> FSM:
        self.stop >> '' >> other.start
        self.stop = other.stop
        return self

    def __pow__(self: FSM, other: int | None) -> FSM:
        if other is None:
            self.stop >> '' >> self.start
            return FSM('') + self
        return functools.reduce(operator.mul, map(
            lambda x: cp(x), [self] * other), FSM(''))

    def dimple(self: FSM) -> str:
        id_map: dd[Node, int] = dd(lambda: len(id_map) + 1)
        res = io.StringIO()
        print(id_map[self.start], file=res)
        print(file=res)
        for n in self.start.bfs():
            id_map[n]
            if n.stop or n == self.stop:
                print(id_map[n], file=res)
        print(file=res)
        for n in self.start.bfs():
            for label, nl in n.next.items():
                for nn in nl:
                    print(id_map[n], id_map[nn], label, file=res)
        res.seek(0)
        return res.read()

    @staticmethod
    def from_dimple(text_str: str) -> FSM:
        text = [line.split() for line in text_str.strip().splitlines()]
        start = text[:text.index([])]
        text = text[len(start) + 1:]
        stop = text[:text.index([])]
        text = text[len(stop) + 1:]
        assert len(start) == 1
        name_to_node: dd[str, Node] = dd(Node)
        res = FSM()
        res.start = name_to_node[start[0][0]]
        for line in stop:
            name_to_node[line[0]].stop = True
        for line in text:
            if len(line) == 2:
                line.append('')
            name_to_node[line[0]] >> line[2] >> name_to_node[line[1]]
        return res
