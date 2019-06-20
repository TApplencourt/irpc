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




class Provider:

    def __init__(self, ProvDef):
        self.provdef = ProvDef

    ######################################################################
    # / ____|  / ____|        | |      | \ | |                           #
    #| |      | |     ___   __| | ___  |  \| | __ _ _ __ ___   ___  _    #
    #| |      | |    / _ \ / _` |/ _ \ | . ` |/ _` | '_ ` _ \ / _ \/ __| #
    #| |____  | |___| (_) | (_| |  __/ | |\  | (_| | | | | | |  __/\__ \ #
    # \_____|  \_____\___/ \__,_|\___| |_| \_|\__,_|_| |_| |_|\___||___/ #
    ######################################################################

    @property
    def entity_name(self):
        return self.provdef.decl.name.split('provide_').pop()

    @property
    def memo_flag_name(self):
        return f'{self.entity_name}_provided'

    @property
    def c_touch_name(self):
        return f'touch_{self.entity_name}'

    #################################################################
    #     /\    / ____|__   __| | \ | |/ __ \|  __ \|  ____|/ ____| #
    #    /  \  | (___    | |    |  \| | |  | | |  | | |__  | (___   #
    #   / /\ \  \___ \   | |    | . ` | |  | | |  | |  __|  \___ \  #
    #  / ____ \ ____) |  | |    | |\  | |__| | |__| | |____ ____) | #
    # /_/    \_\_____/   |_|    |_| \_|\____/|_____/|______|_____/  #
    #################################################################

    @property
    def memo_flag_node(self):
        entity_flag = self.entity_name
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


def is_provider(funcdef: FuncDef):
    return funcdef.decl.name.startswith('provide_')

def provider_name(provdef: ProvDef):
    return provdef.decl.name.split('provide_').pop()

def entity_memo_flag(entity):
    return f'{entity}_provided'

def gen_memo_flag_node(entname):
    entity_flag = entity_memo_flag(entname) 
    type_ = TypeDecl(declname = entity_flag,
                     quals=[], type=IdentifierType(names=['bool']))
    return Decl(name=entity_flag, quals=[],
                storage=[], funcspec=[],
                type= type_, init= ID(name='False'),
                bitsize=None)



def hoist_declaration(main: FuncDef,
                      provdef: ProvDef):


    # Generate "f('bool {entname} = False') 

    provider_info = Provider(provdef)
    entname = provider_info.entity_name
    l_node = provider_info.provdef.body.block_items

    # Move the declaration of the entity and the top of the file
    # All add the declaration of the flag variable for the memoization
    for i, node in enumerate(l_node):
        if isinstance(node,Decl) and node.type.declname == entname:
            node = l_node.pop(i)

            # Entity Declaration
            main.insert(0, node)

            # is_provided Boolean
            main.insert(1, provider_info.memo_flag_node)

            # touch_entity function
            modified_touch_node = provider_info.touch_definition_node

            # Set entity touched is_provided() to true (so the new value is used)
            self_touch = provider_info.memo_flag_node
            self_touch.init.name = 'True'
            modified_touch_node.body.block_items.insert(0,self_touch)

            # Create false entries for all others
            for k, v in adjacency_graph.items():
                if (entname == k):
                    for value in v:
                        modified_touch_node.body.block_items.insert(0, gen_memo_flag_node(value))
            main.insert(2, modified_touch_node)
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
                  adjacency_graph[e].add(provider_name(funcdef))
                  compound.block_items.insert(0, provider_call)
        
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

    adjacency_graph = defaultdict(set)
    for f in l_func:
        add_provider_call(f, l_ent)

    for p in l_provider:
        hoist_declaration(ast.ext, p)

    generator = c_generator.CGenerator()
    print(generator.visit(ast))
