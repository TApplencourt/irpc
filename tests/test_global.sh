#!/bin/bash

# Output checking
./irpc.py ./examples/simple.irp.c > tests/simple.c
diff ./tests/gold.simple.c tests/simple.c
