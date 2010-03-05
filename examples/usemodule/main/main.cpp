#include "integer.h"
#include <stdio.h>

int main()
{
	Integer integer;

	integer.add(5);
	integer.sub(2);

    printf("The result is %d.\n", integer.getValue());

    return 0;
}
