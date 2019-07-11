#include <stdio.h>
#include <math.h>

void provide_x(){
    float x;
    x = 1;
}

void provide_f(){
    float f;
    f  = cos(x) - x;
}

void provide_fprime(){
    float fprime;
    fprime = -sin(x) - 1;
}

void provide_x_next(){
    float x_next;
    x_next = x - f / fprime;
}

int main(){
    printf("x %f\n", x);

    while ( (x- x_next) > 1.e-9) {
        x = x_next;
        touch_x();
        x_next ;
    }
    printf("x convergerded %f\n", x);
}
