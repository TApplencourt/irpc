#!/usr/bin/env python3

from pycparser.c_ast import FuncDef
from irpc.ASTprocessing import CommWorld

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


if __name__ == "__main__":

    from pycparser import parse_file, c_parser, c_generator
    import sys

    filename = sys.argv[1]
    headers, text = remove_headers(filename)

    parser = c_parser.CParser()
    ast = parser.parse(text)

    l_func = { f for f in ast.ext if isinstance(f, FuncDef) }
    world = CommWorld(l_func)
    world.insert_provider_calls()
    world.hoist_declarations(ast.ext)
    world.insert_touches_stuff(ast.ext)

    generator = c_generator.CGenerator()
    print(headers)
    print(generator.visit(ast))
