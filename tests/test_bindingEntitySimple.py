from irpc.bindingEntity import entity2CompoundSimple
from pycparser.c_ast import ID

import unittest

class TestBinding(unittest.TestCase):
    from pycparser import c_parser
    parser = c_parser.CParser()

    def src2d(self, src, argv):
        ast = self.parser.parse(src)
        return entity2CompoundSimple(ast.ext[0], set(argv), ID)

#  __
# (_  o ._ _  ._  |  _
# __) | | | | |_) | (/_
#             |

    def test_simple(self):
        src = 'void foo(){ _ = a;}' ''
        d = self.src2d(src, ['a'])
        assert(d["a"][0][0].block_items[0].rvalue.name == "a")
        assert(d["a"][0][1] == 0)


if __name__ == "__main__":
    unittest.main()


