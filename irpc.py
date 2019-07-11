#!/usr/bin/env python3

from pycparser.c_ast import FuncCall, For, While, FuncDef, Return, FuncDecl, ExprList, ID, Decl, TypeDecl, IdentifierType, If, BinaryOp, UnaryOp, Compound, Assignment, Constant, Switch, Case

from irpc.irpctyping import *
from irpc.bindingEntity import entity2Compound, entity2CompoundSimple, touch2entity
from irpc.ASTfactory import ASTfactory

from collections import defaultdict
# Function can:
#   - use entity
#    be a provider
#
# A provider:
#    - provide an entity
#    - is identified by is name

# 1/ Generate the list of entity
# 2/ Inside function body, insert a call to the provider before any usage of an entity.
# 3/ Inside provider body, hoist the entity declaration
def is_provider(funcdef: FuncDef):
    return funcdef.decl.name.startswith('provide_')

def provider_name(provdef: ProvDef):
    return provdef.decl.name.split('provide_').pop()

def hoist_declaration(main: FuncDef,
                      provdef: ProvDef,
                      adjacency_graph):

    entname = provider_name(provdef)
    astfactory = ASTfactory(entname)
    l_node = provdef.body.block_items

    # Move the declaration of the entity and the top of the file
    # All add the declaration of the flag variable for the memoization
    for i, node in enumerate(l_node):
        if isinstance(node,Decl) and node.type.declname == entname:
            node = l_node.pop(i)

            # Entity Declaration
            main.insert(0, node)

            # is_provided Boolean
            main.insert(1, astfactory.memo_flag_node)
            break

def add_provider_call(funcdef: FuncDef,
                      entnames: Set[Entity]):
    if is_provider(funcdef):
        entnames = entnames - set([provider_name(funcdef)])

    # Insert the provider call
    for e, l_compound in entity2Compound(funcdef.body, entnames).items():
          provider_call = ASTfactory(e).cached_provider_call
          for compound in l_compound:
              compound.block_items.insert(0, provider_call)

def gen_par_adjacency_graph(l_provider, l_ent):
    par_adjacency_graph = defaultdict(set)
    for provdef in l_provider:

        entity = provider_name(provdef)
        entnames = l_ent - set([entity])

        # Insert the provider call
        for children_entity, _ in entity2Compound(provdef.body, entnames).items():
            par_adjacency_graph[entity].add(children_entity)

    return par_adjacency_graph

def gen_child_adjacency_graph(l_provider, l_ent):
    child_adjacency_graph = defaultdict(set)

    for provdef in l_provider:
        entity = provider_name(provdef)
        entnames = l_ent - set([entity])

        for parent_entity, _ in entity2Compound(provdef.body, entnames).items():
            child_adjacency_graph[parent_entity].add(entity)

    return child_adjacency_graph

def find_touches(filename):
    l_touch = set()
    with open(filename, 'r') as input:
        for line in input:
            if line.strip().startswith("touch_") and line.strip().endswith("();"):
                l_touch.add(line.strip().split("()").pop(0))
    return l_touch

def gen_touch_declaration(entity,
                          adjacency_graph,
                          main: FuncDef):

    astfact =  ASTfactory(entity)
    touch_def = astfact.touch_definition_node
    touch_decl = astfact.touch_declaration_node
    
    for ent_touched in sorted(adjacency_graph[entity]):
        touch_def.body.block_items.insert(1,ASTfactory(ent_touched).memo_flag_node)
    
    main.insert(len(main)-1, touch_def)
    main.insert(0, touch_decl)

def remove_headers(filename):
    l_header = ['#include <stdbool.h>\n']
    trim_file = []
    with open(filename, 'r') as f:
        for line in f:
            if 'stdbool' in line:
                continue
            a = l_header if line.startswith("#include") else trim_file
            a.append(line)
    return map("".join, (l_header, trim_file))

def insert_provider_call(funcdef: FuncDef,
                         instance_dict):

    # Entity:List[ Tuple[Idx, Compount]]
    #-> 
    # Compound:[Idx]:Set[Entity]
    d = defaultdict(lambda: defaultdict(set))
    for entity, instances in instance_dict.items():
        for compound, index in instances:
                d[compound][index].add(entity)

    for compound in d:
        d_idx_entity = d[compound]
        for index in sorted(d_idx_entity, reverse=True):
            l_entity = d_idx_entity[index]
            for entity in sorted(l_entity):
                provider_call = ASTfactory(entity).cached_provider_call
                compound.block_items.insert(index, provider_call)

if __name__ == "__main__":

    from pycparser import parse_file, c_parser, c_generator
    import sys

    filename = sys.argv[1]
    headers, text = remove_headers(filename)

    parser = c_parser.CParser()
    ast = parser.parse(text)

    l_func = { f for f in ast.ext if isinstance(f, FuncDef) }
    l_provider = { f for f in l_func if is_provider(f) }
    l_sorted_provider = sorted(l_provider, key=provider_name, reverse=True)
    l_ent  = { provider_name(e) for e in l_provider }
    l_touch = find_touches(filename)


    adjacency_graph = gen_child_adjacency_graph(l_provider, l_ent)

    for f in l_func:
        l_ent_adjusted = l_ent - set([provider_name(f)] if is_provider(f) else () )
        insert_provider_call(f, entity2CompoundSimple(f, l_ent_adjusted, ID))

    for p in l_sorted_provider:
        hoist_declaration(ast.ext, p, adjacency_graph)

    # When touching inside a while / for statement should ensure that the entity in statement are reprovided
    for p in l_func:
        for compound, l_e in touch2entity(p,l_ent).items():
            for e in sorted(l_e):
                provider_call = ASTfactory(e).cached_provider_call
                compound.block_items.insert(len(compound.block_items), provider_call)

    for t in l_touch:
        gen_touch_declaration(t.split("touch_").pop(), adjacency_graph, ast.ext)

    generator = c_generator.CGenerator()
    print(headers)
    print(generator.visit(ast))
