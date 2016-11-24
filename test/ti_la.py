# -*- coding:utf-8 -*-
__author__ = 'shangxc'
import timeit


def err():
    if (lambda: None)():
        pass


def no():
    if _no():
        pass

def _err():
    raise Exception

def _no():
    return None


if __name__ == '__main__':
    print(timeit.timeit(err, number=1000000))
    print(timeit.timeit(no, number=1000000))
