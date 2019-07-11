#! /bin/bash -ex

./irpc.py ./tests/touch.irp.c > tests/touch.c
diff -wbB ./tests/gold.touch.c tests/touch.c
gcc tests/touch.c -o tests/touch.exe
./tests/touch.exe > tests/touch.out
diff -wbB tests/gold.touch.out tests/touch.out
