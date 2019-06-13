int a;
bool a_provided = False;
void provide_a()
{
  a = 10;
}

int main()
{
  if (!a_provided)
  {
    provide_a();
    a_provided = true;
  }

  printf("a = %d \n", a);
  return 0;
}


