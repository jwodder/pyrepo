#!/usr/bin/python3
# -*- coding: utf-8 -*-
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
