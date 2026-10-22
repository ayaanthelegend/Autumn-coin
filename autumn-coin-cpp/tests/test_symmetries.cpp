#include "doctest.h"
#include "autumn/model.hpp"
#include "autumn/integrator.hpp"
#include <cmath>

using namespace autumn;

TEST_CASE("Test 6: Symmetries (180 deg invariance and bilateral mirror)") {
    PlateConfig p;
    p.L = 0.020;
    p.h = 0.0015;
    p.rho_s = 9000.0;
    FluidConfig f;
    CoeffsConfig c;
    Model m(p, f, c);

    double dt = 1e-4;
    double t_end = 0.30;
    int n_steps = static_cast<int>(t_end / dt);

    auto run_drop = [&](double th0_deg) {
        State s = { 0.0, 0.0, th0_deg * M_PI / 180.0, 0.0, 0.0, 0.0 };
        double t = 0.0;
        for (int i = 0; i < n_steps; ++i) {
            s = rk4_step(m, t, s, dt);
            t += dt;
        }
        return s;
    };

    // 1. Invariance under 180 deg turn: theta0 vs theta0 + 180 deg
    double angle1 = 25.0;
    double angle2 = 205.0;

    State s1 = run_drop(angle1);
    State s2 = run_drop(angle2);

    // Positions (X, Y) must be identical
    CHECK(s1[0] == doctest::Approx(s2[0]).epsilon(1e-5));
    CHECK(s1[1] == doctest::Approx(s2[1]).epsilon(1e-5));
    // Speed must be identical
    double spd1 = std::hypot(s1[3], s1[4]);
    double spd2 = std::hypot(s2[3], s2[4]);
    CHECK(spd1 == doctest::Approx(spd2).epsilon(1e-5));

    // 2. Mirror symmetry across vertical: theta0 vs 180 - theta0
    double angle_mirror = 180.0 - angle1; // 155 deg
    State s_mir = run_drop(angle_mirror);

    // X should be mirrored: X_mirror = -X
    CHECK(s_mir[0] == doctest::Approx(-s1[0]).epsilon(1e-5));
    // Y should be identical
    CHECK(s_mir[1] == doctest::Approx(s1[1]).epsilon(1e-5));
}
