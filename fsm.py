from __future__ import annotations
from copy import deepcopy as cp
import operator
import functools
import collections
from collections import defaultdict as dd
import typing
import io


class Copyable:
    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, cp(v, memo))
        return result


class Node(Copyable):
    def __init__(self : Node) -> None:
        self.next: dd[str, set[Node]] = dd(set)
        self.stop: bool = False

    def __rshift__(self : Node, label : str) -> tuple[Node, str]:
        return (self, label)

    def __rrshift__(self : Node, left_label : tuple[Node, str]) -> None:
        left, label, right = left_label + (self,)
        left.next[label] |= {right}

    def __hash__(self : Node) -> int:
        return id(self)

    def bfs(self : Node, eps_only : bool = False) -> typing.Generator[Node, None, None]:
        q: collections.deque[Node] = collections.deque()
        q.append(self)
        visited = set()
        while id(n := q.popleft()) if q else 0:
            if n not in visited:
                visited.add(n)
                yield n
                for l in [n.next, ['']][eps_only]:
                    q.extend(n.next[l])


class FSM(Copyable):
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

    def __repr__(self: FSM) -> str:
        id_map: dd[Node, int] = dd(lambda: len(id_map) + 1)
        res = io.StringIO()
        print(id_map[self.start], file=res)
        print(file=res)
        for n in self.start.bfs():
            if n.stop or n == self.stop:
                print(id_map[n], file=res)
        print(file=res)
        for n in self.start.bfs():
            for label, nl in n.next.items():
                for nn in nl:
                    print(id_map[n], id_map[nn], label, file=res)
        res.seek(0)
        return res.read()


