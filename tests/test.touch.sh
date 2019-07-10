./irpc.py ./tests/touch.irp.c > tests/touch.c
if [[ $(diff -wbB ./tests/gold.touch.c tests/touch.c) ]]; then
    echo "Failed Touch Generation Test"
    echo $(diff -wbB ./tests/gold.touch.c tests/touch.c)
else
    echo "Passed Touch Generation Test"
    gcc tests/touch.c -o tests/touch.exe
    ./tests/touch.exe > tests/touch.out
    if [[ $(diff -wbB tests/gold.touch.out tests/touch.out) ]]; then
        echo "Failed Touch Compilation Test"
        echo $(diff -wbB tests/gold.touch.out tests/touch.out)
    else
        echo "Passed Touch Compilation Test"
    fi
fi
