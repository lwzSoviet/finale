#!/usr/bin/python2
# -*- coding: utf-8 -*-
"""
    @Description:
    ~~~~~~
    @Author  : pake
    @Time    : 2021/7/6 10:19
"""
class A():
    def __init__(self,name):
        self.name=name

    def func1(self):
        pickle.loads(self.name)
        return self.name