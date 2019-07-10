#include <stdbool.h>
#include <stdio.h>

void touch_a();
int a;
bool a_provided = false;
int b;
bool b_provided = false;
void provide_a()
{
  a = 10;
}

void provide_b()
{
  if (!a_provided)
  {
    provide_a();
    a_provided = true;
  }

  a = 20;
  touch_a();
  if (!a_provided)
  {
    provide_a();
    a_provided = true;
  }

  b = a;
}

void touch_a()
{
  bool b_provided = false;
}

int main()
{
  if (!b_provided)
  {
    provide_b();
    b_provided = true;
  }

  printf("b = %i", b);
}


