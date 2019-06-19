int foo = 10;

void provide_foo(){
    int foo;
    foo = 0;
}

void provide_a(){
    int a;
    a = 10;
}

void provide_N(){
    int N;
    N = 10;
}

void provide_b(){
    int b;
    b = 10;
    if (foo == 0) {
       for (int i=0; i++; i < N){
            b += foo + a;
        }
    }
}

int main()
{
   printf("b = %d \n",b);
   return 0;
}

