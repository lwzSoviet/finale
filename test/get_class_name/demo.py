#!/usr/bin/python2
# -*- coding: utf-8 -*-
"""
    @Description:
    ~~~~~~
    @Author  : pake
    @Time    : 2021/7/6 10:19
"""
import sys,os

class A():
    def __init__(self,name):
        self.name=name

    def func1(self):
        a = 'aaa'
        b = 'bbb' + sys.argv[1]
        c = a + b + self.name
        os.system(c)

class B():
    def func1(self):
        pass

    def func2(self,a):
        b = 'ping ' + a
        ins = A(b)
        ins.func1()