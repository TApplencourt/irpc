from irpc.irpctyping import *
from pycparser.c_ast import Compound, ID, If, For, BinaryOp, Assignment, FuncCall, ExprList

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
            elif isinstance(node, FuncCall):
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
    from pycparser import c_parser
    parser = c_parser.CParser()

    def src2d(self, src, argv):
        ast = self.parser.parse(src)
        return entity2Compound(ast.ext[0].body, set(argv))

#  __
# (_  o ._ _  ._  |  _
# __) | | | | |_) | (/_
#             |

    def test_simple(self):
        src = 'void foo(){ _ = a;}' ''
        d = self.src2d(src, ['a'])
        assert (d['a'].pop().block_items[0].lvalue.name == '_')

    def test_multiple_entity(self):
        src = 'void foo(){ _ = a + a ;}' ''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 1)
        assert (d['a'].pop().block_items[0].lvalue.name == '_')

    def test_simple_function(self):
        src = 'void foo(){ _ = f(a);}'
        d = self.src2d(src, ['a'])
        assert (d['a'].pop().block_items[0].lvalue.name == '_')

    def test_simple_expresion(self):
        src = 'void foo(){ _ = a+1 ;}'
        d = self.src2d(src, ['a'])
        assert (d['a'].pop().block_items[0].lvalue.name == '_')

    def test_function_expresion(self):
        src = 'void foo(){ _ = foo(a+1) ;}'
        d = self.src2d(src, ['a'])
        assert (d['a'].pop().block_items[0].lvalue.name == '_')

#  _
# /   _  ._   _| o _|_ o  _  ._   _. |
# \_ (_) | | (_| |  |_ | (_) | | (_| |
#

    def test_conditional_host_condition(self):
        src = 'void foo() { if (a) { _; } }'
        d = self.src2d(src, ['a'])
        assert (type(d['a'].pop().block_items[0]) == If)

    def test_conditional_one_branch(self):
        src = 'void foo() { if (_) { x = a; } }'
        d = self.src2d(src, ['a'])
        assert (d['a'].pop().block_items[0].lvalue.name == 'x')

    def test_conditional(self):
        src = 'void foo() { if (_) { x = a; } else { y = b ; } }'
        d = self.src2d(src, ['a', 'b'])
        assert (d['a'].pop().block_items[0].lvalue.name == 'x')
        assert (d['b'].pop().block_items[0].lvalue.name == 'y')

    def test_conditional_hosting(self):
        src = 'void foo() { if (_) { x = a; } else { y = a ; } }'
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 1)
        assert (type(d['a'].pop().block_items[0]) == If)

    def test_conditional_one_branch_hosting_before(self):
        src = '''
void foo() {
   x = a;
   if (_) { y = a; }
}'''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 1)
        assert (d['a'].pop().block_items[0].lvalue.name == 'x')

    def test_conditional_one_branch_hosting_after(self):
        src = '''
void foo() {
   if (_) { y = a; }
   x = a;
}'''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 1)
        assert (type(d['a'].pop().block_items[0]) == If)

    def test_conditional_two_branch_hosting_before(self):
        src = '''
void foo() {
   x = a ;
   if (_) { y = a; } else { z = b; }
}'''
        d = self.src2d(src, ['a', 'b'])
        assert (len(d['a']) == 1)
        assert (d['a'].pop().block_items[0].lvalue.name == 'x')
        assert (d['b'].pop().block_items[0].lvalue.name == 'z')

#  _
# |_ _  ._
# | (_) |
#

    def test_for(self):
        src = ' void foo() { for  (_; _; _ ) { a; } }'
        d = self.src2d(src, ['a'])
        assert (type(d['a'].pop().block_items[0]) == For)

    def test_for_host1(self):
        src = ' void foo() { for  (a; _; _ ) { _; } }'
        d = self.src2d(src, ['a'])
        assert (type(d['a'].pop().block_items[0]) == For)

    def test_for_host2(self):
        src = ' void foo() { for  (_; a; _ ) { _; } }'
        d = self.src2d(src, ['a'])
        assert (type(d['a'].pop().block_items[0]) == For)

    def test_for_host3(self):
        src = ' void foo() { for  (_; _; a ) { _; } }'
        d = self.src2d(src, ['a'])
        assert (type(d['a'].pop().block_items[0]) == For)

#
# |\ |  _   _ _|_  _   _|
# | \| (/_ _>  |_ (/_ (_|
#

    def test_nested_compound(self):
        src = '''
void foo() {
   x = a;
   { y = b; }
}'''
        d = self.src2d(src, ['a', 'b'])
        assert (d['a'].pop().block_items[0].lvalue.name == 'x')
        assert (d['b'].pop().block_items[0].lvalue.name == 'x')

    def test_nested_if(self):
        src = '''
void foo() {
    if (_) {
        x = a;
        if (_) { y = b; }
   }
}'''
        d = self.src2d(src, ['a', 'b'])
        assert (d['a'].pop().block_items[0].lvalue.name == 'x')
        assert (d['b'].pop().block_items[0].lvalue.name == 'y')

    def test_nested_if_hosting(self):
        src = '''
void foo() {
    if (_) {
        x = a;
        if (_) { y = a; }
   }
}'''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 1)
        assert (d['a'].pop().block_items[0].lvalue.name == 'x')

    def test_nested_if_double(self):
        src = '''
void foo() {
    if (_) {
        if (_) { x = a; }
   } else { y = a ; }
}'''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 2)
        assert ( {c.block_items[0].lvalue.name for c in d['a']} == {'x','y'} )

    def test_nested_if_super_hosting_before(self):
        src = '''
void foo() {
    x = a;
    if (_) {
        if (_) { y = a; }
   }
}'''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 1)
        assert (d['a'].pop().block_items[0].lvalue.name == 'x')

    def test_nested_if_super_hosting_after(self):
        src = '''
void foo() {
    if (c1) {
        if (c2) { y = a; }
   }
   x = a;
}'''
        d = self.src2d(src, {'a'})
        assert (len(d['a']) == 1)
        assert (d['a'].pop().block_items[0].cond.name == 'c1')

    def test_nested_if_for(self):
        src = '''
void foo() {
    if (_) {
        x = a;
        for( _ ; _; _) { y = b;}
   }
}'''
        d = self.src2d(src, ['a', 'b'])
        assert (d['a'].pop().block_items[0].lvalue.name == 'x')
        assert (d['b'].pop().block_items[0].lvalue.name == 'x')


#          _
# |\ | __ /   _  ._ _  ._   _      ._   _|
# | \|    \_ (_) | | | |_) (_) |_| | | (_|
#                      |

    def test_simple_compound(self):
        src = '''
void foo() {
    { x = a; }
    { y = a; }
}'''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 1)
        assert (d['a'].pop().block_items[0].block_items[0].lvalue.name == 'x')

    def test_nested_if_else_2(self):
        src = '''
void foo() {
    if (_) {
        if (_) { x = a; }
   } else { y = a; }
}'''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 2)
        assert ( {c.block_items[0].lvalue.name for c in d['a']} == {'x','y'} )

    def test_nested_if_else_3(self):
        src = '''
void foo() {
    if (c1) {
        if (c2) { x = a; }
        else { y = a; }
   } else { z = a; }

}'''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 1)
        assert (d['a'].pop().block_items[0].cond.name == 'c1')

    def test_nested_if_else_4(self):
        src = '''
void foo() {
    if (c1) {
        if (c2) { x = a; }
        else { y = a; }
   }

}'''
        d = self.src2d(src, ['a'])
        assert (len(d['a']) == 1)
        assert (d['a'].pop().block_items[0].cond.name == 'c2')



if __name__ == "__main__":
    unittest.main()
