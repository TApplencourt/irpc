./irpc.py ./examples/simple.irp.c > tests/simple.c
if [ $(diff -wbB ./tests/gold.simple.c tests/simple.c) ]; then
    echo "Failed Simple Test"
    echo $(diff -wbB ./tests/gold.simple.c tests/simple.c)
else
    echo "Passed Simple Generation Test"
    gcc tests/simple.c -o tests/simple.exe
    ./tests/simple.exe > tests/simple.out
    if [ $(diff -wbB tests/gold.simple.out tests/simple.out)]; then
        echo "Failed Simple Compilation Test"
        echo $(diff -wbB tests/gold.simple.out tests/simple.out)
    else
        echo "Passed Simple Compilation Test"
    fi
fi
