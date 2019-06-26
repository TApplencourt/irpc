#!/bin/bash

# Output checking

## Generic Simple
./irpc.py ./examples/simple.irp.c > tests/simple.c
diff ./tests/gold.simple.c tests/simple.c

## Header Removal + Reinjection
./irpc.py ./tests/header_rem_test.c > tests/header_rem.c
diff ./tests/gold.header_rem.c tests/header_rem.c
