#!/bin/bash

../irpc.py ../example/simple.irp.c > cur_test.c;
diff ../example/gold.simple.c cur_test.c;
rm -f cur_test.c
