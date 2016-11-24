# -*- coding:utf-8 -*-
from concurrent.futures import ThreadPoolExecutor
__author__ = 'shangxc'
def aaa(a,b):
    print(1)

if __name__ == '__main__':
    pool = ThreadPoolExecutor(2)
    v = pool.submit(aaa,1,2)


