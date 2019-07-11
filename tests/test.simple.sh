#! /bin/bash -ex

./irpc.py ./examples/simple.irp.c > tests/simple.c
diff -wbB ./tests/gold.simple.c tests/simple.c
gcc tests/simple.c -o tests/simple.exe
./tests/simple.exe > tests/simple.out
