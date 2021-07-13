#!/usr/bin/python2
# -*- coding: utf-8 -*-
"""
    @Description:
    ~~~~~~
    @Author  : pake
    @Time    : 2021/7/6 10:19
"""
import os

def func1(cmd):
    os.system(cmd)

def b(ip):
    cmd='ping '+ip
    func1(cmd)