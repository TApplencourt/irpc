#!/bin/bash -e

# Output checking
./irpc.py ./examples/simple.irp.c > tests/simple.c
diff_results=$(diff -wbB ./tests/gold.simple.c tests/simple.c)
if [ diff_results ]; then
    echo "Failed Simple Test"
    echo $(diff_results)
else
    echo "Passed Simple Test"
    continue
fi
#./irpc.py ./examples/touch.irp.c > tests/touch.c
if [ $(diff -wbB ./tests/gold.touch.c tests/touch.c) ]; then
    echo "Failed Touch Test"
    diff -wbB ./tests/gold.touch.c tests/touch.c
else
    echo "Passed Touch Test"
fi

# Compiling to be sure
gcc tests/simple.c -o tests/simple.exe
./tests/simple.exe > tests/gold.simple.out

# Output checking
if [[ $(diff -wbB ./tests/gold.simple.out tests/simple.out) ]]; then
    echo "Failed Compilation Test"
    diff -wbB ./tests/gold.simple.out tests/simple.out
else
    echo "Passed Compilation Test"
fi

