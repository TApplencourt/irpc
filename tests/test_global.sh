#!/bin/bash -e

# Output checking
./irpc.py ./examples/simple.irp.c > tests/simple.c
diff ./tests/gold.simple.c tests/simple.c

./irpc.py ./examples/touch.irp.c > tests/touch.c
diff ./tests/gold.touch.c tests/touch.c

# Compiling to be sure
gcc tests/simple.c -o tests/simple.exe
./tests/simple.exe > tests/simple.out

# Output checking
diff ./tests/gold.simple.out tests/simple.out
