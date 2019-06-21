#!/usr/bin/env python3

from pycparser.c_ast import FuncCall, FuncDef, FuncDecl, ID, Decl, TypeDecl, IdentifierType, If, UnaryOp, Compound, Assignment, Constant

from irpc.irpctyping import *
from irpc.bindingEntity import entity2Compound

from collections import defaultdict
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
def is_provider(funcdef: FuncDef):
    return funcdef.decl.name.startswith('provide_')

def provider_name(provdef: ProvDef):
    return provdef.decl.name.split('provide_').pop()

class ASTfactory:

    def __init__(self, entity):
        self.entity = entity

    @property
    def memo_flag_name(self):
        return f'{self.entity}_provided'

    @property
    def c_touch_name(self):
        return f'touch_{self.entity}'

    @property
    def provider(self):
        return f'provide_{self.entity}'

    @property
    def memo_flag_node(self):
        entity_flag = self.entity
        type_ = TypeDecl(declname = entity_flag,
                         quals=[], type=IdentifierType(names=['bool']))
        return Decl(name=entity_flag, quals=[],
                    storage=[], funcspec=[],
                    type= type_, init=ID(name='False'),
                    bitsize=None)

    @property
    def touch_definition_node(self):
        type_ = FuncDecl(args=None,
                         type=TypeDecl(declname=self.c_touch_name,
                                       quals=[], type=IdentifierType(names=['void'])))
        return FuncDef(decl=Decl(name=self.c_touch_name,
                                 quals=[], storage=[],
                                 funcspec=[], type=type_,
                                 init=None, bitsize=None),
                       param_decls=None, body=Compound(block_items=[]))


    @property
    def cached_provider_call(self):
        provider = self.provider
        entity_flag = self.memo_flag_name
        return If(cond=UnaryOp(op='!', expr=ID(name=entity_flag)),
                  iftrue=Compound(block_items=[ FuncCall(name=ID(name=provider), args=None),
                                                Assignment(op='=',
                                                           lvalue=ID(name=entity_flag),
                                                           rvalue=Constant(type='bool', value='True'))]),
                  iffalse=None)

def hoist_declaration(main: FuncDef,
                      provdef: ProvDef, adjacency_graph):


    # Generate "f('bool {entname} = False') 
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

            # touch_entity function
            modified_touch_node = astfactory.touch_definition_node

            # Set entity touched is_provided() to true (so the new value is used)
            self_touch = astfactory.memo_flag_node
            self_touch.init.name = 'True'
            modified_touch_node.body.block_items.insert(0,self_touch)

            # Create false entries for all others
            for value in adjacency_graph[entname]:
                modified_touch_node.body.block_items.insert(0, gen_memo_flag_node(value))

            main.insert(2, modified_touch_node)
            break

def add_provider_call(funcdef: FuncDef,
                      entnames: Set[Entity]):
    if is_provider(funcdef):
        entnames = entnames - set([provider_name(funcdef)])

    # Insert the provider call
    for e, l_compound in entity2Compound(funcdef.body, entnames).items():
          provider_call = ASTfactory(e).cached_provider_call
          for compound in l_compound:
              if is_provider(funcdef):
                  compound.block_items.insert(0, provider_call)

def gen_adjacency_graph(l_provider, l_ent):
    adjacency_graph = defaultdict(set)
    for provdef in l_provider:

        entity = provider_name(provdef)
        entnames = l_ent - set([entity])

        # Insert the provider call
        for children_entity, _ in entity2Compound(provdef.body, entnames).items():
            adjacency_graph[entity].add(children_entity)

    return adjacency_graph

if __name__ == "__main__":

    from pycparser import parse_file, c_parser, c_generator
    import sys

    filename = sys.argv[1]
    ast = parse_file(filename,
                     use_cpp=True,
                     cpp_path='gcc',
                     cpp_args=['-E'])

    l_func = { f for f in ast.ext if isinstance(f, FuncDef) }
    l_provider = { f for f in l_func if is_provider(f) }
    l_ent  = { provider_name(e) for e in l_provider }

    adjacency_graph = gen_adjacency_graph(l_provider, l_ent)


    for f in l_func:
        add_provider_call(f, l_ent)

    for p in l_provider:
        hoist_declaration(ast.ext, p, adjacency_graph)

    generator = c_generator.CGenerator()
    print(generator.visit(ast))
