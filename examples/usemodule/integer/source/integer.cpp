#include "integer.h"

Integer::Integer()
: m_value(0)
{
}

void Integer::add(int value)
{
	m_value += value;
}

void Integer::sub(int value)
{
	m_value -= value;
}

int Integer::getValue() const
{
	return m_value;
}
