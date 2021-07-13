#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    @Description: Configure file
    ~~~~~~
    @Author  : pake
    @Time    : 2021/5/13 10:08
"""
import re

WHITE_FUNCTIONS=['self.get','self.add','self.delete','self.has_key','__init__','ClassCall:LocMemCache.get','ClassCall:PickleSerializer.loads']

# 'archive.extract','os.path.join',
DANGER_FUNCTIONS=['eval','os.system','subprocess.Popen','Popen','pickle.load','pickle.loads','cPickle.load',
                'cPickle.loads','commands.getstatusoutput','commands.getoutput','commands.getstat',]
# 'os.path.join','extractall','extract',

CONTROLLABLE=['sys.argv','BaseRequest']

MAX_LOOP=3

WHITE_FILE_REGEX=re.compile('test')

OUTPUT='./output'

