#!/bin/bash -ex

runing_test () {
        pathTest=./examples/$1.irp.c
        pathC=tests/$1.c
        pathG=./tests/gold.$1.c
        pathE=tests/$1.exe
        pathO=tests/$1.out

        ./irpc.py $pathTest > $pathC
        diff -wbB $pathG $pathC
        gcc $pathC -o $pathE -lm
        ./$pathE > $pathO
  }


runing_test "simple"
runing_test "newton"
