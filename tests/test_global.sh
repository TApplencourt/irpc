#!/bin/bash -e

# Output checking
./irpc.py ./examples/simple.irp.c > tests/simple.c
diff ./tests/gold.simple.c tests/simple.c

# Compiling to be sure
gcc tests/simple.c -o tests/simple.exe
./tests/simple.exe > tests/simple.out

# Output checking
diff ./tests/gold.simple.out tests/simple.out
