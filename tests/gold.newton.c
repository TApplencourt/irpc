#include <stdbool.h>
#include <stdio.h>
#include <math.h>

void touch_x();
float f;
bool f_provided = false;
float fprime;
bool fprime_provided = false;
float x;
bool x_provided = false;
float x_next;
bool x_next_provided = false;
void provide_x()
{
  x = 1;
}

void provide_f()
{
  if (!x_provided)
  {
    provide_x();
    x_provided = true;
  }

  f = cos(x) - x;
}

void provide_fprime()
{
  if (!x_provided)
  {
    provide_x();
    x_provided = true;
  }

  fprime = (-sin(x)) - 1;
}

void provide_x_next()
{
  if (!x_provided)
  {
    provide_x();
    x_provided = true;
  }

  if (!fprime_provided)
  {
    provide_fprime();
    fprime_provided = true;
  }

  if (!f_provided)
  {
    provide_f();
    f_provided = true;
  }

  x_next = x - (f / fprime);
}

void touch_x()
{
  bool f_provided = false;
  bool x_next_provided = false;
}

int main()
{
  if (!x_provided)
  {
    provide_x();
    x_provided = true;
  }

  printf("x %f\n", x);
  if (!x_next_provided)
  {
    provide_x_next();
    x_next_provided = true;
  }

  if (!x_provided)
  {
    provide_x();
    x_provided = true;
  }

  while ((x - x_next) > 1.e-9)
  {
    if (!x_next_provided)
    {
      provide_x_next();
      x_next_provided = true;
    }

    if (!x_provided)
    {
      provide_x();
      x_provided = true;
    }

    x = x_next;
    touch_x();
    if (!x_next_provided)
    {
      provide_x_next();
      x_next_provided = true;
    }

  }

  if (!x_provided)
  {
    provide_x();
    x_provided = true;
  }

  printf("x convergerded %f\n", x);
}


