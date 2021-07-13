#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    @Description: The core of final.
    ~~~~~~
    @Author  : pake
    @Time    : 2021/1/5 14:20
"""
import py3ast
import os
import re
import sys
from pyecharts import Tree
from config import WHITE_FUNCTIONS, MAX_LOOP, WHITE_FILE_REGEX, DANGER_FUNCTIONS, OUTPUT, CONTROLLABLE


class Visitor(py3ast.NodeVisitor):
    """
    Visitor traversal AST,See more in https://docs.python.org/3.7/library/ast.html
    """
    def __init__(self,source_file):
        py3ast.NodeVisitor.__init__(self, )
        self.source_file=source_file
        self.dangerous_calls=[]

    def visit_Call(self,node):
        """
        Detect dangerous function-call,like eval(),os.system(),subporcess.Ppen(),etc.
        :param node:
        :return:
        """
        if isinstance(node.func, py3ast.Name):
            if node.func.id in DANGER_FUNCTIONS:
                self.dangerous_calls.append((self.node_id-1,node.func.id,node.lineno,self.source_file))
        elif isinstance(node.func, py3ast.Attribute):
            func_id=[]
            temp=node.func
            while isinstance(temp, py3ast.Attribute):
                func_id.append(temp.attr)
                temp=temp.value
                # self.node_id+=1
            if isinstance(temp, py3ast.Name):
                func_id.append(temp.id)
                func_id.reverse()
                func_id='.'.join(func_id)
            if func_id in DANGER_FUNCTIONS:
                for i in node.args:
                    # detect if constant
                    if isinstance(i, py3ast.Name):
                        self.dangerous_calls.append((self.node_id - 1, func_id, temp.lineno, self.source_file))
                        break
                    elif isinstance(i,py3ast.Attribute):
                        self.dangerous_calls.append((self.node_id - 1, func_id, temp.lineno, self.source_file))
            # class method call
            else:
                for i in DANGER_FUNCTIONS:
                    if 'ClassCall:' in i and isinstance(func_id,str) and func_equals_classcall(func_id,i):
                        self.dangerous_calls.append((self.node_id - 1, i, temp.lineno, self.source_file,func_id))
                        break
        py3ast.NodeVisitor.generic_visit(self, node)

class Point():
    def __init__(self,source,lineno,param,func_name,call_target,assigns):
        """
        :param source: source file path
        :param lineno: bad code line number
        :param param: param of function
        :param func_name: function name
        :param call_target: call target
        :param assigns list of assigns
        """
        self.source=source
        self.lineno=lineno
        self.param=param
        self.func_name=func_name
        self.call_target=call_target
        self.assigns=assigns

    def __str__(self):
        return 'Source:{source}, lineno:{lineno}, param:{param}, func_name:{func_name}, call_target:{call_target}'.format(
            source=self.source,lineno=self.lineno,param=self.param,func_name=self.func_name,call_target=self.call_target
        )

class ProjectError(Exception):
    def __str__(self):
        print("analysis_project() needs a dir not a file.")

class Taint(Point):
    def __init__(self,source,lineno,param,func_name,call_target,assigns,controllable_assigns):
        Point.__init__(self,source,lineno,param,func_name,call_target,assigns,)
        self.controllable_assigns=controllable_assigns

    def __str__(self):
        return 'Taint:{assigns}, Source:{source}, lineno:{lineno}, param:{param}, func_name:{func_name}, call_target:{call_target}'.format(
            assigns=self.controllable_assigns,source=self.source, lineno=self.lineno, param=self.param, func_name=self.func_name,
            call_target=self.call_target
        )

def get_all_paths(point, paths):
    for i in point.call_target:
        if isinstance(i, str):
            paths.append(i)
            return paths
        elif isinstance(i, Point):
            paths.append(i)
            return get_all_paths(i, paths)

def func_equals_classcall(call_name,classcall_name):
    func_name=classcall_name.split(':',1)[1].split('.',1)[1]
    call_func_name = call_name.split('.')[-1]
    if call_func_name == func_name:
        return classcall_name

def add_node_id(root,id):
    """
    Add id to root, e.g.,root={'name': 'Module', 'children': [{'name': 'Import', 'children': [{'name': 'sss'}]}]}
    this function will change root to {'name': 'Module', 'id':1,'children': [{'name': 'Import', 'id':2,'children': [{'name': 'sss','id':3}]}]}
    """
    if isinstance(root,dict):
        root['id']=id
        id+=1
        if 'children' in root:
            children=root['children']
            for i in children:
                id=add_node_id(i,id)
        return id

def get_node(root,id):
    """
    Get the node by id
    :param root: ast(dict)   e.g.,b={'name': 'Module', 'id':1,'children': [{'name': 'Import', 'id':2,'children': [{'name': 'sss','id':3}]}]}
    :param id:  node_id   e.g.,3
    :return: node(dict)    e.g.,{'name': 'sss','id':3}
    """
    node_id=root['id']
    if node_id==id:
        return root
    if 'children' in root:
        children=root['children']
        for i in children:
            ret=get_node(i,id)
            if ret is not None:
                return ret

def get_name_value(root):
    """
    Get Name node value
    :param root: node
    :return: Str value
    """
    # {'name': 'Name', 'children': [{'name': 'str(str=data)', 'id': 374}, {'name': 'Store', 'id': 375}], 'id': 373}
    if root['name']=='Name':
        return root['children'][0]['name']
    # {'name': 'str(str=argv)', 'id': 35}
    elif re.search(r'str\(str=(.*?)\)',root['name']):
         return root['name']
    elif root['name']=='Attribute':
        children=root['children']
        ret=[]
        for i in children:
            t = get_name_value(i)
            if t and t!='Load':
                ret.append(t)
        # sys.argv
        return '.'.join([re.search(r'str\(str=(.*?)\)',attr).group(1) if 'str(str=' in attr else attr for attr in ret])
    # e.g.,# add(name="123"),assign: ['str(str=name)', '123']
    elif root['name']=='keyword':
        children=root['children']
        ret=[]
        for i in children:
            t = get_name_value(i)
            if t and t!='Load':
                ret.append(t)
        return '######'.join(ret)
    else:
        if 'children' in root:
            children = root['children']
            ret=[]
            for i in children:
                t = get_name_value(i)
                if t and t!='Load':
                    ret.append(t)
            return '######'.join(ret)

def get_arg_value(root):
    """
    Get the formal parameter
    :param root:
    :return:
    """
    if root['name']=='arg':
        return root['children'][0]['name']
    else:
        if 'children' in root:
            children = root['children']
            ret=[]
            for i in children:
                t = get_arg_value(i)
                if t:
                    ret.append(t)
            return '######'.join(ret)

def get_all_assigns(root,block_range):
    """
    Get all assigns between begin id and end id
    :param root:
    :param block_range: (begin_id,end_id)
    :return:
    """
    block_begin,block_end=block_range[0],block_range[1]
    if root['id'] < block_begin:
        if 'children' in root:
            children=root['children']
            ret = []
            for i in children:
                t=get_all_assigns(i,block_range)
                if t:
                    ret.append(t)
            if ret:
                return '$$$$$$'.join(ret)
    elif root['id']<block_end:
        if root['name']=='Assign':
            left = get_name_value(root['children'][0])
            right=get_name_value(root['children'][1])
            return 'left:%s,right:%s'%(left,right)
        # formal parameter
        elif root['name']=='arguments' and root['id']==block_begin+2:
            ret=[]
            for i in root['children']:
                # if i['name']=='Name':
                if i['name'] == 'arg':
                    left = get_arg_value(i)
                    # formal parameter
                    right = 'fp'
                    ret.append('left:%s,right:%s' % (left, right))
            return '$$$$$$'.join(ret)
        # for xxx in xxx
        elif root['name']=='For':
            left = get_name_value(root['children'][0])
            right = get_name_value(root['children'][1])
            return 'left:%s,right:%s' % (left, right)
        else:
            if 'children' in root:
                children = root['children']
                ret=[]
                for i in children:
                    t=get_all_assigns(i, block_range)
                    if t:
                        ret.append(t)
                if ret:
                    return '$$$$$$'.join(ret)

def get_all_functiondef(root):
    """
    Get all FunctionDef nodes
    :param root:
    :return:
    """
    if root['name']=='FunctionDef':
        # block(FunctionDef) begin id
        begin_id=root['id']
        end_id=get_end_id(root)
        return 'begin:%s,end:%s'%(begin_id,begin_id+end_id-1)
    else:
        if 'children' in root:
            t=[]
            for i in root['children']:
                temp=get_all_functiondef(i)
                if temp:
                    t.append(temp)
            return '$$$$$$'.join(t)

def get_all_classdef(root):
    """
    Get all ClassDef nodes
    :param root:
    :return:
    """
    if root['name']=='ClassDef':
        # block(ClassDef) begin id
        begin_id=root['id']
        end_id=get_end_id(root)
        return 'begin:%s,end:%s'%(begin_id,begin_id+end_id-1)
    else:
        if 'children' in root:
            t=[]
            for i in root['children']:
                temp=get_all_classdef(i)
                if temp:
                    t.append(temp)
            return '$$$$$$'.join(t)

def get_end_id(node,num=0):
    """
    Get end-id of node
    :param node:
    :param num:
    :return:
    """
    num+=1
    if 'children' in node:
        children=node['children']
        for i in children:
            num=get_end_id(i,num)
        return num
    else:
        return num

def is_good_function(function_name):
    if function_name in WHITE_FUNCTIONS:
        return True

def is_valid_details_name(name,function_name):
    if name=='self':
        return False
    if '.' in function_name:
        if name in function_name.split('.'):
            return False
    else:
        if name==function_name:
            return False
    return True

def is_tracked(assign_list,name):
    """
    Detect if param can be tracked
    :param assign_list:
    :param name:
    :return:
    """
    for i in assign_list:
        l=i[0]
        r=i[1]
        if name==l:
            # formal parameter
            if 'fp' in r:
                return True
            else:
                if isinstance(r, list):
                    for j in r:
                        if 'self.' in j:
                            rtn = is_tracked(assign_list[:assign_list.index(i)], 'self')
                        else:
                            rtn = is_tracked(assign_list[:assign_list.index(i)], j)
                        if rtn:
                            return rtn

def is_controllable(assign_list,name):
    """
    Detect if param is user-controllable
    :param assign_list:
    :param name: list
    :return:
    """
    controllable_assigns=[]
    for i in assign_list:
        l=i[0]
        r=i[1]
        if name==l:
            for ctrl in CONTROLLABLE:
                if ctrl in r:
                    controllable_assigns.append((r, ctrl))
                    return controllable_assigns
            if 'fp' in r:
                return False
            else:
                if isinstance(r, list):
                    for j in r:
                        rtn=is_controllable(assign_list[:assign_list.index(i)],j)
                        if rtn:
                            return rtn

def get_call_abstract(call):
    """
    Get abstract of call
    :param call: Call node
    :return: e.g., function name$$$$$$arg1$$$$$$arg2
    """
    if call['name']=='Attribute':
        return get_name_value(call)
    elif call['name']=='Name':
        return get_name_value(call)
    elif 'children' in call:
        t = []
        for i in call['children']:
            temp = get_call_abstract(i)
            if temp:
                t.append(temp)
                # a.func()==>a.func(a)
                if '.' in temp:
                    t.append(temp.split('.')[0])
        return '$$$$$$'.join(t)
    else:
        pass

def details2list(call_details):
    """
    :param call_details: str e.g.,'pickle.loads$$$$$$str(str=name)'
    :return: list e.g.,['pickle.loads','name']
    """
    rtn=[]
    a=call_details.split('$$$$$$')
    for i in a:
        search = re.search(r'str\(str=(.*?)\)', i)
        if search:
            rtn.append(search.group(1))
        elif '.' in i:
            rtn.append(i)
        else:
            rtn.append(i)
    return rtn

def assign2list(all_assigns):
    all_assigns_list=[]
    for i in all_assigns.split('$$$$$$'):
        l = i.split(',')[0]
        r = i.split(',')[1]
        if '######' in l:
            left = []
            for temp_left in l.split('######'):
                if '=' in temp_left:
                    left.append(temp_left.split('=')[1].split(')')[0])
                elif ':' in temp_left:
                    left.append(temp_left.split(':')[1])
                else:
                    left.append(temp_left)
        else:
            if '=' in l:
                left = l.split('=')[1].split(')')[0]
            elif ':' in l:
                left = l.split(':')[1]
            else:
                left = l
        t = r.split('######')
        right = []
        for j in t:
            if j:
                if j == 'right:fp':
                    right.append('fp')
                else:
                    # right:str(str=b)
                    if '=' in j:
                        t2 = re.findall('=(.*?)\)', j)
                        if t2:
                            right.extend(t2)
                    else:
                        # attribute，right:sys.argv
                        if 'right:' in j:
                            t2 = j.split('right:', 1)[1]
                            right.append(t2)
                        else:
                            right.append(j)
        if isinstance(left, list):
            for temp_left in left:
                all_assigns_list.append((temp_left, right))
        else:
            all_assigns_list.append((left, right))
    return all_assigns_list

def ins_is_class(ins,classname,assigns):
    for i in assigns:
        left,right=i[0],i[1]
        if left==ins:
            if classname in right:
                return True

def get_class_name(classcall):
    return re.search(r'ClassCall:(.*?)\.',classcall).group(1)

def print_paths(cfgs):
    for cfg in cfgs:
        print('-------------------------------------Call Paths-------------------------------------')
        a = get_all_paths(cfg, [cfg,])
        for i in range(len(a)):
            if i < len(a) - 1:
                print(a[i], '=======>')
            else:
                print(a[i])

def gen_chains(cfg):
    """
    Return chains if generated a Taint.
    :param cfg:
    :return:
    """
    new_cfg=[]
    stat=0
    for i in cfg:
        # assigns is a list
        assigns=i.assigns
        controllable_assigns=is_controllable(assigns,i.param)
        if controllable_assigns:
            taint=Taint(i.source,i.lineno,i.param,i.func_name,i.call_target,i.assigns,controllable_assigns=controllable_assigns)
            new_cfg.append(taint)
            stat=1
        else:
            new_cfg.append(i)
    if stat:
        return new_cfg

def analysis(source_file,evils):
    """
    Analyse single file
    :param source_file: source file path
    :param evils: list of dangerous functions
    :return: new_danger_functions
    """
    global DANGER_FUNCTIONS
    if not os.path.exists(source_file):
        print('%s not found.' % source_file)
    else:
        if isinstance(evils,dict):
            DANGER_FUNCTIONS=[k for k in evils.keys()]
        else:
            DANGER_FUNCTIONS=evils
        new_danger_functions={}
        with open(source_file,encoding='utf8')as f:
            source_code = f.read()
            root = py3ast.parse(source_code)
            node_dict= py3ast.literal_eval(py3ast.echarts_dump(root))
            v = Visitor(source_file)
            v.visit(root)
        # add node_id
        add_node_id(node_dict,1)
        dangerous_calls=v.dangerous_calls
        for m in dangerous_calls:
            call_node_id=m[0]
            call_node=get_node(node_dict,call_node_id)
            call_details=details2list(get_call_abstract(call_node))
            if call_details:
                functiondef_rtn=get_all_functiondef(node_dict)
                functiondef_list = [(n.split(',')[0], n.split(',')[1]) for n in functiondef_rtn.split('$$$$$$')] if functiondef_rtn else []
                classdef_rtn=get_all_classdef(node_dict)
                classdef_list=[(n.split(',')[0], n.split(',')[1]) for n in classdef_rtn.split('$$$$$$')] if classdef_rtn else []
                call_in_functiondef=0
                for k in functiondef_list:
                    begin_id = int(k[0].split(':')[1])
                    end_id = int(k[1].split(':')[1])
                    # if call in FunctionDef
                    if call_node_id > begin_id and call_node_id < end_id:
                        call_in_functiondef = 1
                        all_assigns = get_all_assigns(node_dict, (begin_id, end_id))
                        if all_assigns:
                            all_assigns_list=assign2list(all_assigns)
                        else:
                            continue
                        for name in call_details:
                            if is_valid_details_name(name,m[1]) and is_tracked(all_assigns_list, name):
                                print('Risk call in function:%s, Param:%s, Source:%s, Lineno:%s' % (m[1], name, m[3], m[2]))
                                functiondef_name=re.search(r'\(str=(.*?)\)',get_node(node_dict,begin_id+1)['name']).group(1)
                                if isinstance(evils,dict):
                                    if '.' not in m[1]:
                                        iteration_code = 0
                                        for call_target in evils[m[1]]:
                                            if call_target.func_name == functiondef_name:
                                                iteration_code = 1
                                                break
                                        #  avoid iteration
                                        if iteration_code:
                                            continue
                                false_danger_call=0
                                for classdef in classdef_list:
                                    classdef_begin_id = int(classdef[0].split(':')[1])
                                    classdef_end_id = int(classdef[1].split(':')[1])
                                    # call in ClassDef
                                    if begin_id > classdef_begin_id and end_id < classdef_end_id:
                                        classdef_name = re.search(r'\(str=(.*?)\)',get_node(node_dict, classdef_begin_id + 1)['name']).group(1)
                                        if len(m)==5:
                                            real_call=m[4]
                                            m1_classcall_name=get_class_name(m[1])
                                            # e.g.,self.xxx()
                                            if 'self.' in real_call:
                                                if m1_classcall_name!=classdef_name:
                                                    false_danger_call=1
                                                    break
                                            # e.g.,instance.xxx()
                                            elif re.search(r'^[a-z]',real_call):
                                                ins=real_call.split('.')[0]
                                                if not ins_is_class(ins,m1_classcall_name,all_assigns_list):
                                                    false_danger_call = 1
                                                    break
                                        functiondef_name='ClassCall:'+'.'.join([classdef_name,functiondef_name])
                                        break
                                if false_danger_call:
                                    break
                                # add point into cfg
                                if isinstance(evils, dict):
                                    point = Point(source=m[3], lineno=m[2], param=name, func_name=functiondef_name,
                                                  call_target=evils[m[1]],assigns=all_assigns_list)
                                else:
                                    point = Point(source=m[3], lineno=m[2], param=name, func_name=functiondef_name,
                                                  call_target=[m[1], ],assigns=all_assigns_list)
                                # whitelist
                                if not is_good_function(functiondef_name):
                                    if functiondef_name in new_danger_functions.keys():
                                        new_danger_functions[functiondef_name].append(point)
                                    else:
                                        new_danger_functions[functiondef_name] = [point, ]
                                break
                # if call is out of functiondef
                if not call_in_functiondef:
                    print('Risk call out of function! Call:%s, Source:%s, Lineno:%s' % (
                        m[1], m[3], m[2]))
        return new_danger_functions

def analysis_project(dir,):
    """
    Analyze single source file.
    :param dir:
    :return:
    """
    sources=[]
    # single
    if not os.path.isdir(dir):
        sources.append(dir)
    else:
        for root, dirs, files in os.walk(dir, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                if file_path.endswith('.py') and not re.search(WHITE_FILE_REGEX, file_path):
                    sources.append(file_path)
    cfg = []
    t = DANGER_FUNCTIONS
    loop=0
    scanned = []
    while t and loop<MAX_LOOP:
        new={}
        for i in sources:
            try:
                rtn=analysis(i, t)
            except SyntaxError as e:
                print(e)
            else:
                for k, v in rtn.items():
                    if k in new.keys():
                        new[k].extend(v)
                    else:
                        new[k] = v
        t=new
        for k, v in t.items():
            for i in v:
                # duplicate removal
                point=str(i)
                if point not in scanned:
                    cfg.append(i)
                    scanned.append(point)
        loop += 1
    # debug
    print_paths(cfg)
    print('***************************************END DEBUG***************************************')
    chains=gen_chains(cfg)
    if chains:
        print_paths(chains)

def print_ast(source_file):
    """
    Display ast structrue using pyecharts,it will create ./output/render.html,you can see a Ast-Tree by visiting render.html using browser.
    Replace C:\Python27\Lib\site-packages\pyecharts\charts\tree.py
    Replace C:\Python27\Lib\site-packages\pyecharts\chart.py
    :param source_file:
    :return:
    """
    if os.path.isdir(source_file):
        print('Error: print_ast() needs a file path not dir.')
    elif not os.path.exists(source_file):
        print('%s not found.'%source_file)
    else:
        with open(source_file,encoding='utf8')as f:
            file_name=source_file.split('\\')[-1]
            source_code=f.read()
            data= py3ast.echarts_dump(py3ast.parse(source_code))
            data= py3ast.literal_eval(data)
            tree = Tree('AST of %s'%source_file,height=800,width=1200)
            # tree_collapse_interval=2,initialTreeDepth='-1':default expand,tree_label_text_size=9,tree_leaves_text_size=9
            tree.add("", [data,], tree_orient='TB',initialTreeDepth='1')
            saved_path=os.path.join(OUTPUT,f'{file_name}.html')
            tree.render(saved_path)
            print(f'AST of {source_file} is saved in {saved_path}')

if __name__=="__main__":
    project_dir=sys.argv[1]
    if os.path.isfile(project_dir):
        print_ast(project_dir)
    analysis_project(project_dir)