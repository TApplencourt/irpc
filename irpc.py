#!/usr/bin/env python3

import sys, copy
from pycparser import parse_file, c_parser, c_generator
from pycparser.c_ast import *

from typing import Dict, Set, Tuple, List
EntityName = str
IdName = str

AstNode = Node


#                
# | | _|_ o |  _ 
# |_|  |_ | | _> 
#                
class cached_property(object):
     """
     A property that is only computed once per instance and then replaces itself
     with an ordinary attribute. Deleting the attribute resets the property.
     Source: https://github.com/bottlepy/bottle/commit/fa7733e075da0d790d809aa3d2f53071897e6f76
     """ 

     def __init__(self, func):
         self.__doc__ = getattr(func, '__doc__')
         self.func = func

     def __get__(self, obj, cls):
         if obj is None:
             return self
         value = obj.__dict__[self.func.__name__] = self.func(obj)

         return value


#       __ ___    _                       
#  /\  (_   |    | \  _   _  _  _  ._ _|_ 
# /--\ __)  |    |_/ (/_ _> (_ (/_ | | |_ 
#                                         

# AST of one function:
# The goal is to find all the entity utilization and to bind it to the compound-statements.
# A compound-statement can be a : - the body of the function,
#                                 - the body of if/else statement
#                                 - the body of the forloop

# Notes:
#    - Variable can be used multiple time in the same compound
#    - Variable can be used in multiple compound
#
# 1/ Variable can be used multiple time in the same compound
#   - No problem
# 2/ Variable can be used in multiple compound.
#    We distinguish two types of compound: the one leaving inside conditional statement (A) and the other (B).
#    Rule:
#       If the same variable is used in only B statement, we bind it to all the B statements.
#       If the same variable is used in only A statements, we bind it to all the A statements 
#       If the same variable is used in B and A statements, we bind it the first B statements who enclose the A staments. 
#
#  We split the entity into two group:
#       - The entity who can still be hosted (maybe in the for loop body, maybe if the both branches of the conditional)
#       - The one we can't
#
from typing import NamedTuple
from collections import defaultdict

class Employee():
        def __init__(self, s = None, d = None):
            self.s = s if s is not None else set()
            self.d = d if d is not None else defaultdict(list)

        def add(self, v):
            self.s.add(v)

        def update(self,d):
            for k,v in d.items():
                self.d[k].extend(v)

        # adding two objects
        def __ior__(self, e):
            self.update(e.d)
            self.s.update(e.s)
            return self

        def __and__(self,e):
            n = Employee(self.s & e.s, self.d)
            n.update(e.d)
            return n

def EntityInCompound_rec(l_node,nodes_aloyed, compound) -> Tuple[Dict[IdName, Set[Compound]], 
                                                                 Set[IdName]]:
    l_node_to_recurse = set ()
    e = Employee()

    for node in l_node:
        if isinstance(node, ID):
            if node.name in nodes_aloyed:
                e.add(node.name)            
                nodes_aloyed = nodes_aloyed - e.s
        elif isinstance(node, BinaryOp):
            l_node_to_recurse |= { node.left, node.right }
        elif isinstance(node, Assignment):
            l_node_to_recurse |= { node.lvalue, node.rvalue }
        elif isinstance(node, FuncCall):
            l_node_to_recurse |= set(node.args)
        elif isinstance(node, ExprList):
            l_node_to_recurse |= set(node.exprs)
        elif isinstance(node, Compound):
            e |= Entity2Compound(node, nodes_aloyed)
            nodes_aloyed = nodes_aloyed - e.s

    if l_node_to_recurse:
        e |= EntityInCompound_rec(l_node_to_recurse, nodes_aloyed, compound)
        nodes_aloyed = nodes_aloyed - e.s

    return e

def Entity2Compound(compound, l_entity) -> Tuple[Dict[IdName, Set[Compound]],
                                                 Set[IdName]]:
    
    l = compound.block_items
    head =  [x for x in l if not isinstance(x,(If,For))]
    tail_if  = [x for x in l if isinstance(x,If)]
    tail_for  = [x for x in l if isinstance(x,For)]

    
    e = Employee()

    # Bound to this current compound
    e |= EntityInCompound_rec(head,l_entity, compound)
    l_entity = l_entity - e.s

    # All the entity in the for loop will be bound to this particular compound
    for f in tail_for:
        l_ast_node = [f.init,f.cond,f.next] + f.stmt.block_items
        e |= EntityInCompound_rec(l_ast_node, l_entity, compound)
        l_entity  = l_entity - e.s

    # If statement:
    #     - entity in the cond belong to this compound
    #     - entity in the if  and else branches belong in this compound
    #     - entity in one of the branch are in belong to their compound

    for i in tail_if:
        e |= EntityInCompound_rec([i.cond],l_entity, compound)
        l_entity = l_entity - e.s

        e_t = EntityInCompound_rec([i.iftrue], l_entity, i.iftrue)
        e_f = EntityInCompound_rec([i.iffalse], l_entity, i.iffalse) if i.iffalse else Employee(set(), {})

        # Update the with with the union of the two
        e |=  (e_t & e_f)
        l_entity = l_entity - e.s

        # Update the rest with the correct compound who work
        e.update({e1: [i.iftrue] for e1 in e_t.s - e.s} )
        e.update({e1: [i.iffalse] for e1 in e_f.s - e.s} )

    return e

def Entity2Compoundf(compound, s_entity):
        en = Entity2Compound(compound, s_entity)
        en.update({e: [compound] for e in en.s })
        return en.d

#______               _     _           
#| ___ \             (_)   | |          
#| |_/ / __ _____   ___  __| | ___ _ __ 
#|  __/ '__/ _ \ \ / / |/ _` |/ _ \ '__|
#| |  | | | (_) \ V /| | (_| |  __/ |   
#\_|  |_|  \___/ \_/ |_|\__,_|\___|_|   
#                                       

def provider_name(funcdef):
    if funcdef.decl.name.startswith('provide_'):
        return funcdef.decl.name.split('provide_')[-1]
    else:
        return None

class ProvDef(FuncDef):
    " Provider Definition"
 
    def __init__(self, funcdef, defined_entity):
        self.funcdef = copy.deepcopy(funcdef)
        self.defined_entity = defined_entity
        
    @cached_property
    def name(self) -> str:
        return provider_name(self.funcdef)

    @cached_property
    def entity_to_potentially_provide(self):
        return self.defined_entity - {self.name}

    @cached_property   
    def d_entity_compound(self) -> Dict[EntityName, Set[Compound]]:
       "Filter the dictionary of IdName to only the Entity"
       return Entity2Compoundf(self.funcdef.body, self.entity_to_potentially_provide)

    @cached_property
    def d_compound_entity(self) ->  Dict[Compound, Set[EntityName]]:
        from collections import defaultdict
        d_compound_entity = defaultdict(set)

        for name, lc, in self.d_entity_compound.items():
            for c in lc:
                d_compound_entity[c].add(name)

        return d_compound_entity

    @cached_property
    def ast_with_provider_decl(self):
        """
         1/ Add the provider call to the AST
         2/ Extract the declaration of the AST
        """

        # Dangerous: Modify the ast in place...
        ast = self.funcdef    

        bi, decl = ast.body.block_items, None

        # Corner case to avoid empty block_items
        if bi is None:
            return ast, decl

        if self.name is not None:
            # Remove the declaration of the variale
            for i,block_item in enumerate(bi):
                if isinstance(block_item, Decl) and block_item.type.declname == self.name:
                        del bi[i]
                        decl = block_item
                        break

        # Insert the provider call
        for k,l_e in self.d_compound_entity.items():
             for e in sorted(l_e):
                f = FuncCall(name=ID(name=f'provide_{e}'),args=None)
                k.block_items.insert(0,f)

        return ast,decl

    @cached_property
    def ast_with_provider(self):
        return self.ast_with_provider_decl[0]

    @cached_property
    def entity_decl(self):
        return self.ast_with_provider_decl[1]

# _    _                                        
#| |  | |                                       
#| |  | | __ _ _ __   _ __ ___   ___  _ __ ___  
#| |/\| |/ _` | '__| | '__/ _ \ / _ \| '_ ` _ \ 
#\  /\  / (_| | |    | | | (_) | (_) | | | | | |
# \/  \/ \__,_|_|    |_|  \___/ \___/|_| |_| |_|
#                                               

class IRPc(object):

    def __init__(self, ast):
        self.ast = ast
    
    @cached_property    
    def entities(self) -> Set[EntityName]:
        
        s = set()
        for f in self.ast:
             if isinstance(f,FuncDef):
                name = provider_name(f)
                if name is not None:
                    s.add(name)  
        return s

    @cached_property
    def new_ast(self):
        # For each function add the provider call.
        # Note that ProvDef is bad name. 
        # Indeed we use this call for real provider definition (aka when name is not None)
        # and for function we use some provider (when name is None) but don't provide one (`main` function is one good example)
        ast = copy.deepcopy(self.ast) 

        l_decl = []
        for i,f in enumerate(self.ast):
             if isinstance(f,FuncDef):
                    q = ProvDef(f,self.entities)
                    ast.ext[i] = q.ast_with_provider       
                    if q.name is not None:
                        l_decl.append(q.entity_decl)

        for c in l_decl:
            ast.ext.insert(0,c)
 
        return ast

#------------------------------------------------------------------------------

# _____         _   _             
#|_   _|       | | (_)            
#  | | ___  ___| |_ _ _ __   __ _ 
#  | |/ _ \/ __| __| | '_ \ / _` |
#  | |  __/\__ \ |_| | | | | (_| |
#  \_/\___||___/\__|_|_| |_|\__, |
#                            __/ |
#                           |___/ 

import unittest
class TestBinding(unittest.TestCase):

    parser = c_parser.CParser()

    def src2d(self,src, argv):
        ast = self.parser.parse(src)
        return Entity2Compoundf(ast.ext[0].body, set(argv))

#  __                   
# (_  o ._ _  ._  |  _  
# __) | | | | |_) | (/_ 
#             |         

    def test_simple(self):
        src= 'void foo(){ _ = a;}'''
        d = self.src2d(src, ['a'])
        assert ( d['a'][0].block_items[0].lvalue.name == '_')

    def test_multiple_entity(self):
        src= 'void foo(){ _ = a + a ;}'''
        d = self.src2d(src, ['a'])
        assert ( len(d['a']) == 1)
        assert ( d['a'][0].block_items[0].lvalue.name == '_')

    def test_simple_function(self):
        src= 'void foo(){ _ = f(a);}'
        d = self.src2d(src, ['a'])
        assert ( d['a'][0].block_items[0].lvalue.name == '_')

    def test_simple_expresion(self):
        src= 'void foo(){ _ = a+1 ;}'
        d = self.src2d(src, ['a'])
        assert ( d['a'][0].block_items[0].lvalue.name == '_')

    def test_function_expresion(self):
        src= 'void foo(){ _ = foo(a+1) ;}'
        d = self.src2d(src, ['a'])
        assert ( d['a'][0].block_items[0].lvalue.name == '_')

#  _                                   
# /   _  ._   _| o _|_ o  _  ._   _. | 
# \_ (_) | | (_| |  |_ | (_) | | (_| | 
#                                      
    def test_conditional_host_condition(self):
        src= 'void foo() { if (a) { _; } }'
        d = self.src2d(src, ['a'])
        assert ( type(d['a'][0].block_items[0]) == If)

    def test_conditional_one_branch(self):
        src= 'void foo() { if (_) { x = a; } }'
        d = self.src2d(src, ['a'])
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')

    def test_conditional(self):
        src= 'void foo() { if (_) { x = a; } else { y = b ; } }'
        d = self.src2d(src, ['a','b'])
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')
        assert ( d['b'][0].block_items[0].lvalue.name == 'y')

    def test_conditional_hosting(self):
        src= 'void foo() { if (_) { x = a; } else { y = a ; } }'
        d = self.src2d(src, ['a'])
        assert ( len(d['a']) == 1)
        assert ( type(d['a'][0].block_items[0]) == If)

    def test_conditional_one_branch_hosting_before(self):
        src= '''
void foo() {
   x = a;
   if (_) { y = a; }
}'''
        d = self.src2d(src, ['a'])
        assert ( len(d['a']) == 1)
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')

    def test_conditional_one_branch_hosting_after(self):
        src= '''
void foo() {
   if (_) { y = a; }
   x = a;
}'''
        d = self.src2d(src, ['a'])
        assert ( len(d['a']) == 1)
        assert ( type(d['a'][0].block_items[0]) == If)

    def test_conditional_two_branch_hosting_before(self):
        src= '''
void foo() {
   x = a ;
   if (_) { y = a; } else { z = b; }
}'''
        d = self.src2d(src, ['a','b'])
        assert ( len(d['a']) == 1)
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')
        assert ( d['b'][0].block_items[0].lvalue.name == 'z')

#  _       
# |_ _  ._ 
# | (_) |  
#          
    def test_for(self):
        src= ' void foo() { for  (_; _; _ ) { a; } }'
        d = self.src2d(src, ['a'])
        assert ( type(d['a'][0].block_items[0]) == For)

    def test_for_host1(self):
        src= ' void foo() { for  (a; _; _ ) { _; } }'
        d = self.src2d(src, ['a'])
        assert ( type(d['a'][0].block_items[0]) == For)

    def test_for_host2(self):
        src= ' void foo() { for  (_; a; _ ) { _; } }'
        d = self.src2d(src, ['a'])
        assert ( type(d['a'][0].block_items[0]) == For)

    def test_for_host3(self):
        src= ' void foo() { for  (_; _; a ) { _; } }'
        d = self.src2d(src, ['a'])
        assert ( type(d['a'][0].block_items[0]) == For)

#                         
# |\ |  _   _ _|_  _   _| 
# | \| (/_ _>  |_ (/_ (_| 
#                         
    def test_nested_compound(self):
        src= '''
void foo() {
   x = a;
   { y = b; }
}'''
        d = self.src2d(src, ['a','b'])
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')
        assert ( d['b'][0].block_items[0].lvalue.name == 'x')


    def test_nested_if(self):
        src= '''
void foo() {
    if (_) {
        x = a;
        if (_) { y = b; }
   }
}'''
        d = self.src2d(src, ['a','b'])
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')
        assert ( d['b'][0].block_items[0].lvalue.name == 'y')

    def test_nested_if_hosting(self):
        src= '''
void foo() {
    if (_) {
        x = a;
        if (_) { y = a; }
   }
}'''
        d = self.src2d(src, ['a'])
        assert ( len(d['a']) == 1)
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')

    def test_nested_if_double(self):
        src= '''
void foo() {
    if (_) {
        if (_) { x = a; }
   } else { y = a ; }
}'''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 2 )
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')
        assert ( d['a'][1].block_items[0].lvalue.name == 'y')

    def test_nested_if_super_hosting_before(self):
        src= '''
void foo() {
    x = a;
    if (_) {
        if (_) { y = a; }
   }
}'''
        d = self.src2d(src, ['a'])
        assert ( len(d['a']) == 1)
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')

    def test_nested_if_super_hosting_after(self):
        src= '''
void foo() {
    if (c1) {
        if (c2) { y = a; }
   }
   x = a;
}'''
        d = self.src2d(src, {'a'})
        assert ( len(d['a']) == 1)
        assert ( d['a'][0].block_items[0].cond.name == 'c1' )

    def test_nested_if_for(self):
        src= '''
void foo() {
    if (_) {
        x = a;
        for( _ ; _; _) { y = b;}
   }
}'''
        d = self.src2d(src, ['a','b'])
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')
        assert ( d['b'][0].block_items[0].lvalue.name == 'x')

#          _                               
# |\ | __ /   _  ._ _  ._   _      ._   _| 
# | \|    \_ (_) | | | |_) (_) |_| | | (_| 
#                      |                   

    def test_simple_compound(self):
        src= '''
void foo() {
    { x = a; } 
    { y = a; }
}'''
        d = self.src2d(src, ['a'])
        assert ( len(d['a']) == 1)
        assert ( d['a'][0].block_items[0].block_items[0].lvalue.name == 'x')

    def test_nested_if_else_2(self):
        src= '''
void foo() {
    if (_) {
        if (_) { x = a; }
   } else { y = a; }
}'''
        d = self.src2d(src, ['a'])
        assert ( len(d['a']) == 2)
        assert ( d['a'][0].block_items[0].lvalue.name == 'x')
        assert ( d['a'][1].block_items[0].lvalue.name == 'y')

    def test_nested_if_else_3(self):
        src= '''
void foo() {
    if (c1) {
        if (c2) { x = a; } 
        else { y = a; }
   } else { z = a; }
   
}'''
        d = self.src2d(src, ['a'])
        assert ( len(d['a']) == 1)
        assert ( d['a'][0].block_items[0].cond.name == 'c1')

    def test_nested_if_else_4(self):
        src= '''
void foo() {
    if (c1) {
        if (c2) { x = a; }
        else { y = a; }
   }

}'''
        d = self.src2d(src, ['a'])
        assert ( len(d['a']) == 1)
        assert ( d['a'][0].block_items[0].cond.name == 'c2')

if __name__ == "__main__":

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        ast = parse_file(filename, use_cpp=True,
                        cpp_path='gcc',
                        cpp_args=['-E'])
    
        a = IRPc(ast)
        generator = c_generator.CGenerator()
        print (generator.visit(a.new_ast))
    else:
        unittest.main()

