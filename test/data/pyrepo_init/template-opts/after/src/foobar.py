"""
A project

Visit <https://github.com/jwodder/foobar-project-name> or
<https://foobar-project-name-docs.rtfd.io> for more information.
"""

__version__ = "0.1.0.dev1"
__author__ = "John Thorvald Wodder II"
__author_email__ = "foobar-project-name@example.com"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/foobar-project-name"

from collections import Counter


def life(before):
    """
    Takes as input a state of Conway's Game of Life, represented as an iterable
    of ``(int, int)`` pairs giving the coordinates of living cells, and returns
    a `set` of ``(int, int)`` pairs representing the next state
    """
    before = set(before)
    neighbors = Counter(
        (x + i, y + j)
        for (x, y) in before
        for i in [-1, 0, 1]
        for j in [-1, 0, 1]
        if (i, j) != (0, 0)
    )
    return {xy for (xy, n) in neighbors.items() if n == 3 or (n == 2 and xy in before)}
