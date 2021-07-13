#!/usr/bin/python2
# -*- coding: utf-8 -*-
"""
    @Description: 
    ~~~~~~
    @Author  : pake
    @Time    : 2021/7/6 10:19
"""

def Add(a,b):
    c=a+b
    return c

class A():
    def __init__(self,name):
        self.name=name

    def func1(self):
        os.system(self.name)
        return self.name