import ast
import queue
import io

count = 0


class Node:
    def __init__(self):
        global count
        self.id = count
        count += 1
        self.next: 'dict[str, list[Node]]' = dict()

# endfsm = list[node] = epsilon non-deterministic finite state machine


def reg2endfsm(root) -> 'endfsm':
    if isinstance(root, str):
        root = ast.parse(root).body[0].value
    if isinstance(root, ast.BinOp):
        if isinstance(root.op, ast.Add):
            start = Node()
            stop = Node()
            left = reg2endfsm(root.left)
            right = reg2endfsm(root.right)
            start.next[''] = [left[0], right[0]]
            left[-1].next[''] = [stop]
            right[-1].next[''] = [stop]
            return [
                start,
                *left,
                *right,
                stop
            ]
        if isinstance(root.op, ast.Mult):
            left = reg2endfsm(root.left)
            right = reg2endfsm(root.right)
            left[-1].next[''] = [right[0]]
            return left + right
        if isinstance(root.op, ast.Pow):
            assert isinstance(root.right, ast.Constant)
            if root.right.value is None:
                start = Node()
                stop = Node()
                left = reg2endfsm(root.left)
                left[-1].next[''] = [left[0], stop]
                start.next[''] = [left[0], stop]
                return [
                    start,
                    *left,
                    stop,
                ]
            else:
                res = ast.Constant(value=1)
                for q in range(root.right.value):
                    res = ast.BinOp(
                        left=res,
                        op=ast.Mult(),
                        right=root.left
                    )
                return reg2endfsm(res)
    elif isinstance(root, ast.Name):
        start = Node()
        stop = Node()
        start.next[root.id] = [stop]
        return [start, stop]
    elif isinstance(root, ast.Constant):
        if root.value in [0, 1]:
            start = Node()
            stop = Node()
            if root.value == 1:
                start.next[''] = [stop]
            return [start, stop]

def iter_edges(endfsm):
    for start in endfsm:
        for label, stops in start.next.items():
            for stop in stops:
                yield (start, label, stop)


def graphviz(endfsm):
    out = io.StringIO()
    print('digraph G{', file=out)
    for node in endfsm:
        print(f'    {node.id}', file=out)
    for start, label, stop in iter_edges(endfsm):
        print(f'    {start.id} -> {stop.id} [ label="{label!r}" ];', file=out)
    print('}', file=out)
    out.seek(0)
    return out.read()


def dimple(endfsm):
    out = io.StringIO()
    print('0', file=out)
    print('', file=out)
    print(len(endfsm) - 1, file=out)
    print('', file=out)
    for start, label, stop in iter_edges(endfsm):
        print(f'{start.id} {stop.id}{f" {label}" if label else str()}', file=out)
    out.seek(0)
    return out.read()


if __name__ == '__main__':
    endfsm = reg2endfsm(input())
    print(graphviz(endfsm), end='')
    print(dimple(endfsm), end='')
