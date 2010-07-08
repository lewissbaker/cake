#ifndef INTEGER_INCLUDED_H
#define INTEGER_INCLUDED_H

#include "module.h"

// Example export class
class MODULE_API Integer
{
public:
	Integer();

	void add(int value);
	void sub(int value);

	int getValue() const;

private:
	int m_value;
};

#endif
