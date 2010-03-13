#include "point.hpp"

Point::Point()
	: _x(0.0f)
	, _y(0.0f)
{
}

Point::Point(float x, float y)
	: _x(x)
	, _y(y)
{
}

float Point::X::get()
{
	return _x;
}

void Point::X::set(float value)
{
	_x = value;
}

float Point::Y::get()
{
	return _x;
}

void Point::Y::set(float value)
{
	_x = value;
}

float Point::Length::get()
{
	return System::Math::Sqrt(_x * _x + _y * _y);
}
