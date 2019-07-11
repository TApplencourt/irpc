#include <stdbool.h>
#include <stdio.h>

void provide_a(){
  int a;
  a = 10;
}

void provide_b(){
  int b;
  a = 20;
  touch_a();
  b = a;
}

int main(){
  printf("b = %i", b);
}
