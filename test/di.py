# -*- coding:utf-8 -*-
__author__ = 'shangxc'

class di(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super().__init__({self[i]: i for i in self})

    def __setitem__(self, *args, **kwargs):
        if args[1] in self:
            self.pop(args[1])
        super().__setitem__(*args, **kwargs)
        super().__setitem__(*reversed(args))

    def pop(self, k, d=None):
        super().pop(self[k], d)
        return super().pop(k, d)





if __name__ == '__main__':
    a = di({})
    a[1] = '2'
    print(a)
    a[3] = '2'
    print(a)
