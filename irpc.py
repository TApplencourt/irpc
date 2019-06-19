#!/usr/bin/env python3

import sys, copy

from collections import defaultdict

from pycparser import c_ast
from pycparser.c_ast import FuncCall, ID, Decl, TypeDecl, FuncDecl, IdentifierType, If, UnaryOp, Compound, Assignment, Constant

from irpc.irpctyping import *
from irpc.bindingEntity import entity2Compound

# Function can:
#   - use entity
#   - be a provider
#
# A provider:
#    - provide an entity
#    - is identified by is name

# 1/ Generate the list of entity
# 2/ Inside function body, insert a call to the provider before any usage of an entity.
# 3/ Inside provider body, hoist the entity declaration

# A visitor with some state information (the funcname it's looking for)

def is_provider(funcdef: FuncDef):
    return funcdef.decl.name.startswith('provide_')

def provider_name(provdef: ProvDef):
    return provdef.decl.name.split('provide_').pop()

def touch_name(entity):
    return f'touch_{entity}'

def entity_memo_flag(entity):
    return f'{entity}_provided'

 # Generate "f('bool {entname} = False') 
def ast_entity_memo_flag(entname):
    entity_flag = entity_memo_flag(entname) 
    type_ = TypeDecl(declname = entity_flag,
                     quals=[], type=IdentifierType(names=['bool']))
    return Decl(name=entity_flag, quals=[],
                storage=[], funcspec=[],
                type= type_, init= ID(name='False'),
                bitsize=None)

def touch_declaration(main: FuncDef,
                      provdef: ProvDef):
    touch_name_decl = touch_name(entname)
    type_ = FuncDecl(args=None, type=TypeDecl(declname = touch_name_decl,
                                              quals=[], type=IdentifierType(names=['void'])))
    return Decl(name=touch_name_decl,
                quals=[], storage=[], funcspec=[],
                type= type_,
                init= None,
                bitsize=None)

def touch_definition(entname):
    touch_name_decl = touch_name(entname)
    type_ = FuncDecl(args=None, type=TypeDecl(declname = touch_name_decl,
                                              quals=[], type=IdentifierType(names=['void'])))
    return FuncDef(decl=Decl(name=touch_name_decl, quals=[],storage=[],funcspec=[],type=type_, init=None, bitsize=None), param_decls=None, body=Compound(block_items=[]))


def hoist_declaration(main: FuncDef,
                      provdef: ProvDef):       
        
    entname = provider_name(provdef)
    l_node = provdef.body.block_items
    # Move the declaration of the entity and the top of the file
    # All add the declaration of the flag variable for the memoization
    for i, node in enumerate(l_node):
        if isinstance(node,Decl) and node.type.declname == entname:
            node = l_node.pop(i)

            # Insert Declaration 
            main.insert(0, node)

            # Insert Memo Flag
            main.insert(1, ast_entity_memo_flag(entname))

            # Setup and Insert Touch_*() function
            new = touch_definition(entname)

            # Insert Memo Flag = True for respective entity's touch function
            self_touch_element = ast_entity_memo_flag(entname)
            self_touch_element.init.name='True'
            new.body.block_items.insert(0, self_touch_element)

            # Add false flags to all adjacent nodes in the upward graph
            for k,v in upward_graph.items():
                if (entname == k):
                    for value in v:
                        new.body.block_items.insert(0, ast_entity_memo_flag(value))
            main.insert(2,new)
            break

def add_provider_call(funcdef: FuncDef,
                      entnames: Set[Entity]):
    # Generated "f{ if (!entity_memo_flag{entity}) { call provider_{entity} ; entity_memo_flag{entity} = True}
    def ast_cached_provider_call(entity):
              provider = f'provide_{entity}'
              entity_flag = entity_memo_flag(entity)
              return If(cond=UnaryOp(op='!', expr=ID(name=entity_flag)),
                        iftrue=Compound(block_items=[ FuncCall(name=ID(name=provider), args=None),
                                                      Assignment(op='=',
                                                                 lvalue=ID(name=entity_flag),
                                                                 rvalue=Constant(type='bool', value='True'))]),
                                                      iffalse=None)

    if is_provider(funcdef):
        entnames = entnames - set([provider_name(funcdef)])

    # Insert the provider call
    for e, l_compound in entity2Compound(funcdef.body, entnames).items():
        provider_call = ast_cached_provider_call(e)
        for compound in l_compound:
            if is_provider(funcdef):
                prov_name = funcdef.decl.name.split('provide_').pop()
                downward_graph[prov_name].add(e)
                upward_graph[e].add(prov_name)
                compound.block_items.insert(0, provider_call)

    

if __name__ == "__main__":

    from pycparser import parse_file, c_parser, c_generator

    filename = sys.argv[1]
    ast = parse_file(filename,
                     use_cpp=True,
                     cpp_path='gcc',
                     cpp_args=['-E'])

    downward_graph = defaultdict(set)
    upward_graph = defaultdict(set)

    l_func = { f for f in ast.ext if isinstance(f, FuncDef) }
    l_provider = { f for f in l_func if is_provider(f) }
    l_ent  = { provider_name(e) for e in l_provider }

    for f in l_func:
            add_provider_call(f, l_ent)
        
    for p in l_provider:
        hoist_declaration(ast.ext, p)

    generator = c_generator.CGenerator()
    
    print(generator.visit(ast))
