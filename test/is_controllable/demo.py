#!/usr/bin/python2
# -*- coding: utf-8 -*-
"""
    @Description:
    ~~~~~~
    @Author  : pake
    @Time    : 2021/7/6 10:19
"""
import sys,pickle

def func1(name):
    a='aaa'
    b='bbb'+sys.argv[1]
    c=a+b+name
    pickle.loads(c)