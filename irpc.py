#!/usr/bin/env python3

from pycparser.c_ast import FuncCall, For, While, FuncDef, Return, FuncDecl, ExprList, ID, Decl, TypeDecl, IdentifierType, If, BinaryOp, UnaryOp, Compound, Assignment, Constant, Switch, Case

from irpc.irpctyping import *
from irpc.bindingEntity import entity2Compound

from collections import defaultdict
from itertools import groupby
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

    def gen_memo_flag_node(self,self_touch):
        val = 'true' if self_touch else 'false'
        type_ = TypeDecl(declname = self.memo_flag_name,
                         quals=[], type=IdentifierType(names=['bool']))
        return Decl(name=self.entity, quals=[],
                    storage=[], funcspec=[],
                    type= type_, init=ID(name=val),
                    bitsize=None)

    @property
    def memo_flag_node_self(self):
        return self.gen_memo_flag_node(True)

    @property
    def memo_flag_node(self):
        return self.gen_memo_flag_node(False)
    
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
    def touch_declaration_node(self):
        return FuncDecl(args=None,
                        type=TypeDecl(declname=self.c_touch_name,
                                      quals=[], type=IdentifierType(names=['void'])))
    @property
    def cached_provider_call(self):
        provider = self.provider
        entity_flag = self.memo_flag_name
        return If(cond=UnaryOp(op='!', expr=ID(name=entity_flag)),
                  iftrue=Compound(block_items=[ FuncCall(name=ID(name=provider), args=None),
                                                Assignment(op='=',
                                                           lvalue=ID(name=entity_flag),
                                                           rvalue=Constant(type='bool', value='true'))]),
                  iffalse=None)


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

def node_extract(node):
    if isinstance(node, Compound):
        return node.block_items
    elif isinstance(node, If):
        return [node.iftrue, node.iffalse]
    elif isinstance(node, (While, For) ):
        return [ node.cond, node.stmt ]
    elif isinstance(node, FuncDef):
        return [ node.body ]
    elif isinstance(node, ( Switch, Case ) ):
        return [node.stmts]
    elif isinstance(node, BinaryOp):
        return [node.left, node.right]
    elif isinstance(node, Assignment):
        return [node.lvalue, node.rvalue]
    elif isinstance(node, ID):
        return [node.name]
    elif isinstance(node, ExprList):
        return node.exprs
    elif isinstance(node, FuncCall) and node.args:
        return node.args
    elif  isinstance(node, (Return, Decl, Constant)):
        return []
    elif isinstance(node, UnaryOp):
        return [ node.expr ]
    else:
        return []

def find_instances(astnode, l_ent, _type_, old_compound = None, idx_old_compound = 0):
    """
    Recursively search through AST to locate all instances of ID nodes

    Args:
        param1: Node to be analyzed (ie. FuncDef, Compound, etc)
        param2: Placeholder for current compounds parent (None by default)
        param3: Cached index to maintain integrity of value across recurses (Default 0: ie. No cache)

    Returns:
        Returns a dict of all Compounds containing instances of entity w/ provider
    """
    # d holds all compounds with appropriate index values based on entity occurences
    d = defaultdict(list)
    # Recurses through elements in body of head node

    for i, node in enumerate(node_extract(astnode)):

        if isinstance(node, Compound):
            old_compound = node

        if isinstance(astnode, Compound):
            idx_old_compound = i
        # Append any entries of ID node names to d so long as it is a function with a provider
        if isinstance(node, _type_):
            if node.name in l_ent:
                if d[node.name] == [] or ( d[node.name][-1] != (old_compound, idx_old_compound) ):
                    d[node.name].append( (old_compound, idx_old_compound) )
        # If anything but instance of ID -> recurse
        else:
            # Recursive call followed by updating the dictionary
            for k,v in find_instances(node, l_ent, _type_, old_compound, idx_old_compound).items():
                d[k] += v
    return d

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
    return(l_touch)

def hoist_touch(entity,
                adjacency_graph,
                main: FuncDef):
    touch_def = ASTfactory(entity).touch_definition_node
    touch_decl = ASTfactory(entity).touch_declaration_node
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
            for entity in l_entity:
                provider_call = ASTfactory(entity).cached_provider_call
                compound.block_items.insert(index, provider_call)

if __name__ == "__main__":

    from pycparser import parse_file, c_parser, c_generator
    import sys

    filename = sys.argv[1]
    headers, text = remove_headers(filename)
    l_touch = find_touches(filename)

    parser = c_parser.CParser()
    ast = parser.parse(text)

    l_func = { f for f in ast.ext if isinstance(f, FuncDef) }
    l_provider = { f for f in l_func if is_provider(f) }
    l_sorted_provider = sorted(l_provider, key=provider_name, reverse=True)
    l_ent  = { provider_name(e) for e in l_provider }

    adjacency_graph = gen_child_adjacency_graph(l_provider, l_ent)

    for f in l_func:
        l_ent_adjusted = l_ent - set([provider_name(f)] if is_provider(f) else () )
        insert_provider_call(f, find_instances(f, l_ent_adjusted, ID))

    for p in l_sorted_provider:
        hoist_declaration(ast.ext, p, adjacency_graph)

    for t in l_touch:
        hoist_touch(t.split("touch_").pop(), adjacency_graph, ast.ext)
    generator = c_generator.CGenerator()
    print(headers)
    print(generator.visit(ast))
