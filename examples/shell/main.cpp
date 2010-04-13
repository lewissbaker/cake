#include <stdio.h>

int main(int argc, char **argv)
{
	if (argc == 0)
	{
		printf("ERROR: Expected a parameter.\n");
		return 1;
	}

	printf("The answer is: %s\n", argv[argc - 1]);
    return 0;
}
