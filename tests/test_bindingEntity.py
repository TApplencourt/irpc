from irpc.bindingEntity import entity2Compound
from pycparser.c_ast import Compound, ID, If, For, BinaryOp, Assignment, FuncCall, ExprList

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
