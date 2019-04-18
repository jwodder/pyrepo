#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
A project

Visit <https://github.com/jwodder/foobar> for more information.
"""

__version__      = '0.1.0.dev1'
__author__       = 'John Thorvald Wodder II'
__author_email__ = 'foobar@varonathe.org'
__license__      = 'MIT'
__url__          = 'https://github.com/jwodder/foobar'

import sys

def main():
    if len(sys.argv) > 1:
        qty = int(sys.argv[1])
    else:
        qty = 10
    a,b = 0, 1
    print(b, end='')
    for _ in range(qty):
        a, b = b, a+b
        print(' ' + str(b), end='')
    print()

if __name__ == '__main__':
    main()
