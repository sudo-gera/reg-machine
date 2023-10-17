import ast
import sys
import convert

# each ast object is simply this:
# class ast.****:
#     def __init__(self, **d):
#         self.__dict__.update(d)

def match_longest(node: ast.AST, x: str) -> tuple[
        float, # -1, 0, ... inf  -- max {n | exists str s : s matches x{n}   and s matches node}
        float  #     0, ... inf  -- max {n | exists str s : s matches x{n}.* and s matches node}
    ]:
    # linear as it makes DFS over AST
    # correctness proof is just looking at all cases in code
    this = match_longest
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = this(node.left, x)
        right = this(node.right, x)
        return max(left[0], right[0]), max(left[1], right[1])
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        value = this(node.left, x)
        if value[0] > 0:
            return float('inf'), float('inf')
        return 0, value[1]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        left = this(node.left, x)
        right = this(node.right, x)
        if left[0] == -1:
            return left
        if right[0] == -1:
            return -1, max(left[0] + right[1], left[1])
        return left[0] + right[0], max(left[0] + right[1], left[1])
    if isinstance(node, ast.Name):
        if node.id == x:
            return (1, 1)
        return (-1, 0)
    else:
        return (0, 0)


def parse(reg: str) -> ast.AST:
    # obviously linear and correct
    stack : list[ast.AST] = []
    for pos, c in enumerate(reg):
        if c.isspace():
            continue
        try:
            if c == '+':
                stack.append(ast.BinOp(right = stack.pop(), op = ast.Add(), left = stack.pop()))
            elif c == '.':
                stack.append(ast.BinOp(right = stack.pop(), op = ast.Mult(), left = stack.pop()))
            elif c in '*\u2217':
                stack.append(ast.BinOp(left = stack.pop(), op = ast.Pow(), right = ast.Constant(value = None)))
            elif c == '1':
                stack.append(ast.Constant(value = 1))
            else:
                stack.append(ast.Name(id = c))
        except IndexError:
            raise ValueError(f'Not enough values for operator {c} at pos {pos}.')
    if len(stack) > 1:
        raise ValueError(f'Too many values (got {len(stack)}, expected 1). Perhaps you forgot + or . operator at the end of input?')
    return stack.pop() if stack else ast.Constant(value = 1)

def check(reg: str, x: str, k:int):
    # obviously linear and correct
    root = parse(reg)
    longest = match_longest(root, x)
    return longest[1] >= k

if __name__ == '__main__':
    print('YES' if check(sys.argv[1], sys.argv[2], int(sys.argv[3])) else 'NO')


