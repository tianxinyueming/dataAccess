# -*- coding:utf-8 -*-
__author__ = 'shangxc'
import time
import string


def aaa(f):
    # a = time.time()
    # if a >= 1480625919.1:
    #     return 1
    # if 1 == 1:
    #     return 1
    t = time.time()
    # if t >= 1480625919.1:
    #     return 1
    # if 500000000 > 0:                   # are we rolling over?
    #     if f.tell() >= 500000000:
    #         return 1
    # return 0

def bbb(f):
    # a = int(time.time())
    # if a >= 1480625919.1:
    #     return 1
    # with open('test.txt', 'a') as f:
    #     f.write(string.printable)
    #     # print(f.tell())
    #     # f.tell()
    t = int(time.time())
    # if t >= 1480625919:
    #     return 1
    # # if f is None:                 # delay was set...
    # #     f = f
    # if 500000000 > 0:                   # are we rolling over?
    #     msg = "%s\n" % ("%s" % 'aaa')
    #     f.seek(0, 2)  #due to non-posix-compliant Windows feature
    #     if f.tell() + len(msg) >= 500000000:
    #         return 1
    # return 0


if __name__ == '__main__':
    import timeit
    f = open('test.txt', 'a')
    print(timeit.timeit(lambda :aaa(f)))
    print(timeit.timeit(lambda :bbb(f)))
    import sqlite3
    # f = open('test.txt', 'a')
    # print(f.tell())
    # print(timeit.timeit(f.tell))
    # with open('test.txt', 'a') as f:
    #     print(f.tell())
    #     f.seek(0, 2)
    #     print(f.tell())



