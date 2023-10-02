import sys
sys.path.append('../src/')
import reg2endfsm
def remove_indent(text):
    text = text.splitlines()
    while all([line.startswith(' ') if line else True for line in text]):
        text = [line[1:] for line in text]
    return '\n'.join(text)

def test_simple():
    fsm = reg2endfsm.reg2endfsm('( a + b ) ** None * a * b * ( a + b ) ** None + 1 * ( a + b ) ** 0 * a + b ** 2 + 0')
    test_dim = reg2endfsm.dimple(fsm)
    test_gv = reg2endfsm.graphviz(fsm)
    true_gv_dim = remove_indent('''
        digraph G{
            0
            2
            4
            6
            8
            10
            11
            12
            13
            9
            7
            14
            15
            16
            17
            18
            20
            22
            23
            24
            25
            21
            19
            26
            27
            28
            29
            30
            31
            5
            32
            33
            34
            35
            36
            37
            3
            38
            39
            1
            0 -> 2 [ label="''" ];
            0 -> 38 [ label="''" ];
            2 -> 4 [ label="''" ];
            2 -> 32 [ label="''" ];
            4 -> 6 [ label="''" ];
            4 -> 26 [ label="''" ];
            6 -> 8 [ label="''" ];
            6 -> 7 [ label="''" ];
            8 -> 10 [ label="''" ];
            8 -> 12 [ label="''" ];
            10 -> 11 [ label="'a'" ];
            11 -> 9 [ label="''" ];
            12 -> 13 [ label="'b'" ];
            13 -> 9 [ label="''" ];
            9 -> 8 [ label="''" ];
            9 -> 7 [ label="''" ];
            7 -> 14 [ label="''" ];
            14 -> 15 [ label="'a'" ];
            15 -> 16 [ label="''" ];
            16 -> 17 [ label="'b'" ];
            17 -> 18 [ label="''" ];
            18 -> 20 [ label="''" ];
            18 -> 19 [ label="''" ];
            20 -> 22 [ label="''" ];
            20 -> 24 [ label="''" ];
            22 -> 23 [ label="'a'" ];
            23 -> 21 [ label="''" ];
            24 -> 25 [ label="'b'" ];
            25 -> 21 [ label="''" ];
            21 -> 20 [ label="''" ];
            21 -> 19 [ label="''" ];
            19 -> 5 [ label="''" ];
            26 -> 27 [ label="''" ];
            27 -> 28 [ label="''" ];
            28 -> 29 [ label="''" ];
            29 -> 30 [ label="''" ];
            30 -> 31 [ label="'a'" ];
            31 -> 5 [ label="''" ];
            5 -> 3 [ label="''" ];
            32 -> 33 [ label="''" ];
            33 -> 34 [ label="''" ];
            34 -> 35 [ label="'b'" ];
            35 -> 36 [ label="''" ];
            36 -> 37 [ label="'b'" ];
            37 -> 3 [ label="''" ];
            3 -> 1 [ label="''" ];
            39 -> 1 [ label="''" ];
        }
        0

        39

        0 2
        0 38
        2 4
        2 32
        4 6
        4 26
        6 8
        6 7
        8 10
        8 12
        10 11 a
        11 9
        12 13 b
        13 9
        9 8
        9 7
        7 14
        14 15 a
        15 16
        16 17 b
        17 18
        18 20
        18 19
        20 22
        20 24
        22 23 a
        23 21
        24 25 b
        25 21
        21 20
        21 19
        19 5
        26 27
        27 28
        28 29
        29 30
        30 31 a
        31 5
        5 3
        32 33
        33 34
        34 35 b
        35 36
        36 37 b
        37 3
        3 1
        39 1
    '''[1:])
    assert test_gv + test_dim == true_gv_dim

