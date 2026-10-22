#pragma once

#include <string>
#include <vector>
#include <cmath>
#include <map>
#include <fstream>
#include <sstream>
#include <iostream>

namespace sph {

#ifndef M_PI
constexpr double M_PI = 3.14159265358979323846;
#endif

struct Vec2 {
    double x = 0.0;
    double y = 0.0;

    constexpr Vec2() = default;
    constexpr Vec2(double x_, double y_) : x(x_), y(y_) {}

    constexpr Vec2 operator+(const Vec2& o) const { return {x + o.x, y + o.y}; }
    constexpr Vec2 operator-(const Vec2& o) const { return {x - o.x, y - o.y}; }
    constexpr Vec2 operator-() const { return {-x, -y}; }
    constexpr Vec2 operator*(double s) const { return {x * s, y * s}; }
    constexpr Vec2 operator/(double s) const { return {x / s, y / s}; }

    Vec2& operator+=(const Vec2& o) { x += o.x; y += o.y; return *this; }
    Vec2& operator-=(const Vec2& o) { x -= o.x; y -= o.y; return *this; }
    Vec2& operator*=(double s) { x *= s; y *= s; return *this; }

    double dot(const Vec2& o) const { return x * o.x + y * o.y; }
    double cross(const Vec2& o) const { return x * o.y - y * o.x; }
    double length_sq() const { return x * x + y * y; }
    double length() const { return std::sqrt(length_sq()); }
    Vec2 normalized() const {
        double l = length();
        return (l > 1e-12) ? (*this / l) : Vec2{0.0, 0.0};
    }
};

inline Vec2 operator*(double s, const Vec2& v) { return v * s; }

struct Mat2x2 {
    double m00 = 0.0, m01 = 0.0;
    double m10 = 0.0, m11 = 0.0;

    static Mat2x2 identity() {
        Mat2x2 m;
        m.m00 = 1.0; m.m11 = 1.0;
        return m;
    }

    static Mat2x2 outer_product(const Vec2& a, const Vec2& b) {
        Mat2x2 m;
        m.m00 = a.x * b.x; m.m01 = a.x * b.y;
        m.m10 = a.y * b.x; m.m11 = a.y * b.y;
        return m;
    }

    Mat2x2 operator+(const Mat2x2& o) const {
        Mat2x2 res;
        res.m00 = m00 + o.m00; res.m01 = m01 + o.m01;
        res.m10 = m10 + o.m10; res.m11 = m11 + o.m11;
        return res;
    }

    Mat2x2 operator-(const Mat2x2& o) const {
        Mat2x2 res;
        res.m00 = m00 - o.m00; res.m01 = m01 - o.m01;
        res.m10 = m10 - o.m10; res.m11 = m11 - o.m11;
        return res;
    }

    double inf_norm() const {
        double r0 = std::abs(m00) + std::abs(m01);
        double r1 = std::abs(m10) + std::abs(m11);
        return std::max(r0, r1);
    }
};

struct FluidConfig {
    double rho0 = 998.0;          // Reference fluid density [kg/m^3]
    double mu = 0.001;            // Dynamic viscosity [Pa*s]
    double gamma = 7.0;           // Tait exponent
    double c0 = 50.0;             // Speed of sound [m/s]
    double p_bg = 0.0;            // Background pressure [Pa]
    Vec2 gravity = {0.0, -9.81};  // Gravity [m/s^2]

    double nu() const { return (rho0 > 0.0) ? (mu / rho0) : 0.0; }
};

struct RigidPlateConfig {
    double L = 0.024;             // Chord / major diameter [m]
    double h = 0.0018;            // Thickness / minor diameter [m]
    double rho_s = 7800.0;        // Solid density [kg/m^3]
    Vec2 pos = {0.0, 0.0};        // Initial lab position [m]
    Vec2 vel = {0.0, 0.0};        // Initial lab linear velocity [m/s]
    double theta = 0.0;           // Initial orientation angle [rad]
    double omega = 0.0;           // Initial angular velocity [rad/s]
    bool fixed = false;           // If true, kinematic/fixed body

    double a() const { return L / 2.0; }
    double b() const { return h / 2.0; }
    double area() const { return M_PI * a() * b(); }
    double mass() const { return rho_s * area(); }
    double inertia() const { return 0.25 * mass() * (a() * a() + b() * b()); }
    double I_star(double rho_f = 998.0) const { return (rho_s * h) / (rho_f * L); }
    double U_t(double rho_f = 998.0, double g = 9.81) const {
        double r = (rho_s / rho_f) - 1.0;
        return (r > 0.0) ? std::sqrt(r * g * h) : 0.0;
    }
};

struct SPHConfig {
    double dx = 0.001;            // Initial particle spacing [m]
    double h_factor = 1.3;        // h_sml = h_factor * dx
    double alpha_art = 0.0;       // Artificial viscosity parameter (default 0.0)
    double dt = 1e-4;             // Timestep [s]
    double t_end = 2.0;           // Total simulation time [s]
    double output_dt = 0.01;      // Snapshot output interval [s]
    int picard_iters = 2;         // Picard relaxation iterations for light body
    double omega_relax = 0.5;     // Picard relaxation parameter
    bool use_shepard_density = false; // Optional Shepard normalization for quiescent submerged bodies
    bool compute_pressure = true; // Set to false to isolate pure viscous Laplacian operator

    double h_sml() const { return h_factor * dx; }
    double r_cutoff() const { return 2.0 * h_sml(); }
};

struct DomainConfig {
    double x_min = -0.15;
    double x_max = 0.15;
    double y_min = -0.40;
    double y_max = 0.05;
    bool periodic_x = false;
    bool periodic_y = false;
    int boundary_layers = 4;
};

struct RenderConfig {
    int width = 960;
    int height = 1280;
    double pixels_per_meter = 2000.0;
    bool draw_particles = true;
    bool draw_coin = true;
    bool draw_tank = true;
    std::string color_mode = "speed"; // "speed" or "vorticity"
};

} // namespace sph
