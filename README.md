# What's finale ?
***finale*** is a tool for python code security audit. It use cfg (control flow graph) to analyze source code and find risk, only support python3.x  now.

# Usage
```shell
pip install -r requirements.txt
```

### Demo.py

```python
#!/usr/bin/python2
# -*- coding: utf-8 -*-
import os

def func1(cmd):
    os.system(cmd)

def b(ip):
    cmd='ping '+ip
    func1(cmd)
```

### Run:

```python
python engine.py ./code/demo.py
```

### Output:

```
AST of C:\Users\jliu\finale\code\demo.py is saved in ./output\demo.py.html
Risk call in function:os.system, Param:cmd, Source:C:\Users\jliu\finale\code\demo.py, Lineno:12
Risk call in function:func1, Param:cmd, Source:C:\Users\jliu\finale\code\demo.py, Lineno:16
-------------------------------------Call Paths-------------------------------------
Source:C:\Users\jliu\finale\code\demo.py, lineno:12, param:cmd, func_name:func1, call_target:['os.system'] =======>
os.system
-------------------------------------Call Paths-------------------------------------
Source:C:\Users\jliu\finale\code\demo.py, lineno:16, param:cmd, func_name:b, call_target:[<__main__.Point object at 0x00000290C58A5748>] =======>
Source:C:\Users\jliu\finale\code\demo.py, lineno:12, param:cmd, func_name:func1, call_target:['os.system'] =======>
os.system
***************************************END DEBUG***************************************
```

It will generate a AST of demo.py in ./output/demo.py.html like the following:

![image-20210713175235383](https://github.com/lwzSoviet/download/blob/master/images/image-20210713173845195.png)

# Welcome to PR!

This program is just started and some bugs in it. So welcome to PR.