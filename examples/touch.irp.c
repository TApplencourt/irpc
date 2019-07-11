#include <stdio.h>

void provide_a(){
  int a;
  a = 10;
}

void provide_b(){
  a = 20;
  touch_a();
  int b;
  b = a;
}

int main(){
  printf("b = %i", b);
}
