from irpc.irpctyping import *
from pycparser.c_ast import FuncCall, For, While, FuncDef, Return, FuncDecl, ExprList, ID, Decl, TypeDecl, IdentifierType, If, BinaryOp, UnaryOp, Compound, Assignment, Constant, Switch, Case

#       __ ___    _
#  /\  (_   |    | \  _   _  _  _  ._ _|_
# /--\ __)  |    |_/ (/_ _> (_ (/_ | | |_
#

# AST of one function:
# The goal is to find all the entity utilization and to bind it to the compound-statements.
# A compound-statement can be a : - the body of a function,
#                                 - the body of a if/else statement
#                                 - the body of a loop

# Notes:
#    - Entity can be used multiple time in the same compound
#    - Entity can be used in multiple compound
#
# - If an entity is used in a compound, we don't need to check children's compound (immutability)
# - If an entity is present in both branch of a conditional, it can be hoisted out
# - Similarly, if an entity if present in a loop body, it can be hostied out

from collections import defaultdict
from dataclasses import dataclass, field

def entity2Compound(compound, s_entity) -> Dict[Entity, Set[Compound]]:
    @dataclass
    class EntityWalker:
        n: Set = field(default_factory=set) # Entities we are looking for
        s: Set = field(default_factory=set) # Entities we found that can be hoisted
        d: Dict = field(default_factory=lambda: defaultdict(set)) # Found entities who can't be hoisted

        def add_set(self, v):
            self.s.add(v)
            self.n = self.n - self.s

        def extend_dict(self, d):
            for k, v in d.items():
                self.d[k] |= v

            # Not sure if needed, commenting this line
            # make all the test pass
            # Need to add test who break 
            self.s = self.s - set(self.d.keys())

        def __ior__(self, e):
            self.extend_dict(e.d)
            self.s.update(e.s)
            self.n = self.n - self.s
            return self

        def __and__(self, e):
            s = self.s & e.s
            tmp = EntityWalker(self.n - s, s, self.d)
            tmp.extend_dict(e.d)
            return tmp

    def entity2compound_simple(l_node, nodes_aloyed, compound) -> EntityWalker:
        l_node_to_recurse = set()
        w = EntityWalker(nodes_aloyed)

        for node in l_node:
            if isinstance(node, ID) and node.name in nodes_aloyed:
                w.add_set(node.name)
            elif isinstance(node, Compound):
                w |= entity2compound_hoisting(node, w.n)
            elif isinstance(node, BinaryOp):
                l_node_to_recurse |= {node.left, node.right}
            elif isinstance(node, Assignment):
                l_node_to_recurse |= {node.lvalue, node.rvalue}
            elif isinstance(node, FuncCall) and node.args:
                l_node_to_recurse |= set(node.args)
            elif isinstance(node, ExprList):
                l_node_to_recurse |= set(node.exprs)

        if l_node_to_recurse:
            w |= entity2compound_simple(l_node_to_recurse, w.n, compound)

        return w

    def entity2compound_hoisting(compound, l_entity) -> EntityWalker:

        l = compound.block_items
        head = [x for x in l if not isinstance(x, (If, For))]
        tail_if = [x for x in l if isinstance(x, If)]
        tail_for = [x for x in l if isinstance(x, For)]

        # Bound to this current compound
        w = entity2compound_simple(head, l_entity, compound)

        # All the entity in the for loop will be bound to this particular compound
        for f in tail_for:
            l_ast_node = [f.init, f.cond, f.next] + f.stmt.block_items
            w |= entity2compound_simple(l_ast_node, w.n, compound)

        # If statement:
        #     - entity in the cond -> this compound
        #     - entity in both  branches -> this compound
        #     - entity in one and only one branch -> compound of the associate branch
        for i in tail_if:
            w |= entity2compound_simple([i.cond], w.n, compound)

            w_t = entity2compound_hoisting(i.iftrue, w.n)
            w_f = entity2compound_hoisting(i.iffalse, w.n) if i.iffalse else EntityWalker(w.n)

            # Update with the value who are in both branches
            w |= (w_t & w_f)

            # Update the rest with the compound who are present only on their branch
            w.extend_dict({e: {i.iftrue} for e in w_t.s - w.s})
            w.extend_dict({e: {i.iffalse} for e in w_f.s - w.s})

        return w

    w = entity2compound_hoisting(compound, s_entity)
    # Bound the remaining entity to the current compound
    w.extend_dict({e: {compound} for e in w.s})
    return w.d


def node_extract(node):
    if isinstance(node, Compound):
        return node.block_items if node.block_items else []
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

def entity2CompoundSimple(astnode, l_ent, _type_, old_compound = None, idx_old_compound = 0):
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
    if isinstance(astnode, _type_) and astnode.name in l_ent:
        return {astnode.name : { (old_compound, idx_old_compound) } }

    d = defaultdict(set)
    
    if isinstance(astnode, Compound):
                old_compound = astnode

    # Recurses through elements in body of head node
    for i, node in enumerate(node_extract(astnode)):
        if isinstance(node, Compound):
            old_compound = node

        if isinstance(astnode, Compound):
            idx_old_compound = i
        # Append any entries of ID node names to d so long as it is a function with a provider
        if isinstance(node, _type_):
            if node.name in l_ent:
                #if d[node.name] == [] or ( d[node.name][-1] != (old_compound, idx_old_compound) ):
                d[node.name].add( (old_compound, idx_old_compound) )
        # If anything but instance of ID -> recurse
        else:
            # Recursive call followed by updating the dictionary
            for k,v in entity2CompoundSimple(node, l_ent, _type_, old_compound, idx_old_compound).items():
                d[k] |= v
    return d

# Find the compound associated to the touch
def touch2entity(astnode,l_ent, old_compound=None, old_entity=None):
    d = defaultdict(set)
    for i, node in enumerate(node_extract(astnode)):
        if isinstance(node, (While, For ) ):
            old_entity = set(entity2CompoundSimple(node.cond, l_ent, ID))
            old_compound = node.stmt 

        if isinstance(node, FuncCall) and node.name.name.startswith('touch_'):
            entity_touched = node.name.name.split("touch_").pop()
            d[ (entity_touched, old_compound) ] |= old_entity - set([entity_touched])
        else:
            for k,v in touch2entity(node, l_ent, old_compound, old_entity).items():
                d[k] |= v

    return d


