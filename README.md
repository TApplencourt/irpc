# irpc


[![Build Status](https://travis-ci.org/TApplencourt/irpc.svg?branch=master)](https://travis-ci.org/TApplencourt/irpc)


Compiler to implement IRP method for C

## Requirement

- pycparser


## Example

Disclamer: Don't yet support `#include`

```
./irpc.py example/hw.c > hw_irp.c
sed -i '1s/^/#include <stdio.h>\n/' hw_irp.c
gcc hw_irp.c -o hw_irp 
./hw_irp
```

