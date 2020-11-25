"""
A project

Visit <https://github.com/jwodder/foobar> or <https://foobar.rtfd.io> for more
information.
"""

__version__      = '0.1.0.dev1'
__author__       = 'John Thorvald Wodder II'
__author_email__ = 'foobar@varonathe.org'
__license__      = 'MIT'
__url__          = 'https://github.com/jwodder/foobar'

from collections import Counter

def life(before):
    """
    Takes as input a state of Conway's Game of Life, represented as an iterable
    of ``(int, int)`` pairs giving the coordinates of living cells, and returns
    a `set` of ``(int, int)`` pairs representing the next state
    """
    before = set(before)
    neighbors = Counter(
        (x+i, y+j) for (x,y) in before
                   for i in [-1,0,1]
                   for j in [-1,0,1]
                   if (i,j) != (0,0)
    )
    return {xy for (xy, n) in neighbors.items()
               if n == 3 or (n == 2 and xy in before)}

def signum(x):
    """
    >>> signum(0)
    0
    >>> signum(42)
    1
    >>> signum(-23)
    -1
    """
    return 0 if x == 0 else x / abs(x)
