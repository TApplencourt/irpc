#include <stdio.h>
int b;
int N;
int a;
int foo;
void provide_foo()
{
  foo = 0;
}

void provide_a()
{
  a = 10;
}

void provide_N()
{
  N = 10;
}

void provide_b()
{
  provide_foo();
  b = 10;
  if (foo == 0)
  {
    provide_a();
    provide_N();
    for (int i = 0; i++; i < N)
    {
      b += foo + a;
    }

  }

}

int main()
{
  provide_b();
  printf("b = %d \n", b);
  return 0;
}


