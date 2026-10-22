#pragma once

#include <array>
#include <string>
#include <vector>

namespace autumn {

// State vector: [X, Y, theta, u, v, omega]
// X, Y: Lab frame position (m), Y points up
// theta: Angle of major axis (chord) from +X axis (rad), unwrapped
// u: Body-frame velocity along chord (m/s)
// v: Body-frame velocity along thickness (m/s)
// omega: Angular velocity d(theta)/dt (rad/s)
using State = std::array<double, 6>;

struct Vec2 {
    double x = 0.0;
    double y = 0.0;
};

enum class Outcome {
    Running,
    Bottom,
    Wall,
    Timeout
};

enum class Regime {
    Steady,
    Fluttering,
    Tumbling,
    Mixed
};

struct Sample {
    double t = 0.0;
    double X = 0.0;
    double Y = 0.0;
    double theta = 0.0; // rad
    double omega = 0.0; // rad/s
    double u = 0.0;     // m/s
    double v = 0.0;     // m/s
    double alpha = 0.0; // rad
    double speed = 0.0; // m/s
    double vy = 0.0;    // m/s
};

} // namespace autumn
