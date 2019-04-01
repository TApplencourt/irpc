#!/usr/bin/env python3

import sys, copy
from pycparser import parse_file, c_parser, c_generator
from pycparser.c_ast import *

from typing import Dict, Set
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
     """  # noqa

     def __init__(self, func):
         self.__doc__ = getattr(func, '__doc__')
         self.func = func

     def __get__(self, obj, cls):
         if obj is None:
             return self
         value = obj.__dict__[self.func.__name__] = self.func(obj)

         return value
#                  
# |\/|  _   _. _|_ 
# |  | (/_ (_|  |_ 
#                  
def IdName2Compound_rec(node: AstNode, 
                      d_id: Dict[IdName,Compound],
                      d_lvl: Dict[IdName,int], 
                      compound = None, save_next_compound = True, lvl = 0):
        """Binding the entity to the compound
        Perform hoisting. Only the coumpound at the lower level is saved.
        """             
        l_node = set ()

        if isinstance(node, ID):
             # Provider hoisting
             if d_lvl.get(node.name,lvl) >= lvl:
                  d_id[node.name] =  compound
                  d_lvl[node.name] = lvl
        elif isinstance(node, Compound):
            l_node = set(node.block_items)
            if save_next_compound:
                compound = node
                save_next_compound = False
                lvl += 1
        elif isinstance(node, BinaryOp):
            l_node = { node.left, node.right }
        elif isinstance(node, Assignment):
            l_node = { node.lvalue, node.rvalue }
        elif isinstance(node, FuncCall):
            l_node = set(node.args)
        elif isinstance(node, ExprList):
            l_node = set(node.exprs)
        elif isinstance(node, For):
            l_node = { node.init,node.cond,node.next,node.stmt }
        elif isinstance(node, If):
            l_node = { node.iftrue, node.iffalse, node.cond }
            save_next_compound = True

        for n in l_node:
           IdName2Compound_rec(n,d_id, d_lvl, compound, save_next_compound, lvl)

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
    def d_entity_compound(self) -> Dict[EntityName,Compound]:
       "Filter the dictionary of IdName to only the Entity"
       # Can be done directly inside IdName2Compound_rec
       d = {} ; d_lvl = {}
       IdName2Compound_rec(self.funcdef.body,d,d_lvl)
       return {name : c for name,c in d.items() if name in self.entity_to_potentially_provide} 

    @cached_property
    def d_compound_entity(self) ->  Dict[Compound, Set[EntityName]]:
        from collections import defaultdict
        d_compound_entity = defaultdict(set)
        for name, c, in self.d_entity_compound.items():
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
if __name__ == "__main__":
    
    filename = sys.argv[1]

    ast = parse_file(filename, use_cpp=True,
            cpp_path='gcc',
            cpp_args=['-E'])


    a = IRPc(ast)
    generator = c_generator.CGenerator()
    print (generator.visit(a.new_ast))

