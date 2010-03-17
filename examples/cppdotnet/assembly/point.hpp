public ref class Point
{
public:

	Point();
	Point(float x, float y);

	property float X {
		float get();
		void set(float);
	}
	property float Y {
		float get();
		void set(float);
	}

	property float Length {
		float get();
	}

private:

	float _x;
	float _y;

};
