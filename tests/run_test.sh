#!/bin/bash

cd ..

# Output checking
./irpc.py ./example/simple.irp.c > tests/cur_test.c;
diff ./example/gold.simple.c tests/cur_test.c;
rm -f tests/cur_test.c

#Python unittest
# Will run all the test*.py
python -m unittest discover
