# Regular expression to finite state machine
### regex format:
* `a + b` means `a` or `b`
* `a * b` means `ab`
* `a ** n` means `aaaa...aaa` (n times)
* `a ** None` means `eps` or `a` or `aa` or ...
* `0` means nothing (empty set of possible strings)
* `1` means eps
### regex example:
`(a + 1) * (b + 1)` means `eps` or `a` or `b` or `ab`
## Usage:
`python command.py --operations [OPERATIONS...] --letters LETTERS `
where:    
OPERATIONS is a sequence of operations from this list:
* re-to-eps-nfa
* remove-eps
* make-deterministic
* make-full
* minimize
* invert
* eps-nfa-to-re

`<labels>`  - All labels to be used (alphabet).

##### Note: commands are executed in a given order from left to right. Each of them has preconditions that must be met for it to work, which can be seen by calling --help. Script will refuse to work without them.

# Tests and coverage:
## Preparation:
```
python3 -m pip install pytest coverage
```
## Tests:
```
pytest ./test_all.py
```
## Coverage:
```
./coverage.sh
```
## Result:

    Name          Stmts   Miss  Cover
    ---------------------------------
    command.py      199     16    92%
    convert.py      190      6    97%
    fa.py           120      1    99%
    utils.py         12      3    75%
    validate.py      29      2    93%
    ---------------------------------
    TOTAL           550     28    95%

