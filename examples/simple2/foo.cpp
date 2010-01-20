#include "foo.hpp"
#include <stdio.h>

Foo::Foo()
{
	printf("Foo()\n");
}

Foo::~Foo()
{
	printf("~Foo()\n");
}
