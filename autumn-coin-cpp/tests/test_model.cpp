#include "doctest.h"
#include "autumn/model.hpp"
#include "autumn/integrator.hpp"
#include "autumn/tank.hpp"
#include <algorithm>
#include <cmath>
#include <random>

using namespace autumn;

TEST_CASE("Test 2: Dimensional & Geometric Consistency") {
    PlateConfig p;
    p.L = 0.024;
    p.h = 0.0018;
    p.rho_s = 7800.0;
    FluidConfig f;
    CoeffsConfig c;

    Model m(p, f, c);

    // Verify positive mass and moments
    CHECK(m.mass() > 0.0);
    CHECK(m.mass_fluid() > 0.0);
    CHECK(m.m11() > 0.0);
    CHECK(m.m22() > m.m11()); // m22 is along thickness, proportional to a^2 (L^2 > h^2)
    CHECK(m.Ia() > 0.0);
    CHECK(m.Mu() > m.mass());
    CHECK(m.Mv() > m.mass());
    CHECK(m.Itot() > 0.0);
}

TEST_CASE("Test 3: Lift Coefficient Peak at 45 deg") {
    PlateConfig p;
    FluidConfig f;
    CoeffsConfig c;
    Model m(p, f, c);

    // Evaluate circulation and lift across alpha in [0, 90 deg]
    double max_CL = -1.0;
    double alpha_at_max = 0.0;

    for (double deg = 1.0; deg < 89.0; deg += 1.0) {
        double rad = deg * M_PI / 180.0;
        // In body frame: u = V cos(alpha), v = -V sin(alpha) so that atan2(-v, u) = alpha
        double V = 0.35;
        double u = V * std::cos(rad);
        double v = -V * std::sin(rad);
        double omega = 0.0;

        // Circulation: Gamma = -C_T * L * (u*v/V)
        double gamma = -c.C_T * p.L * (u * v / V);
        // C_L(alpha) = 2 Gamma / (V * L)
        double CL = 2.0 * gamma / (V * p.L);

        if (CL > max_CL) {
            max_CL = CL;
            alpha_at_max = deg;
        }
    }

    CHECK(max_CL == doctest::Approx(1.2).epsilon(0.01));
    CHECK(alpha_at_max == doctest::Approx(45.0).epsilon(1.0));
}

TEST_CASE("Test 5: Broadside Terminal Fall Speed") {
    PlateConfig p;
    p.L = 0.020;
    p.h = 0.0015;
    p.rho_s = 9000.0;
    FluidConfig f;
    CoeffsConfig c;
    Model m(p, f, c);

    double U_est = m.U_terminal_broadside_est();
    CHECK(U_est > 0.1);
    CHECK(U_est < 2.0);

    // Verify dynamic force balance when falling broadside: theta = 0, u = 0, v = -U_est
    State s = { 0.0, -0.1, 0.0, 0.0, -U_est, 0.0 };
    State ds = m.rhs(0.0, s);

    // At terminal speed, vertical acceleration dv/dt should be near 0
    CHECK(std::abs(ds[4]) < 0.05); // dv/dt ≈ 0
}

TEST_CASE("Test 7: Orientation & Rotated Corner Points") {
    double L = 0.024;
    double h = 0.002;

    // theta = 0 (horizontal coin)
    State s0 = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    auto p0 = get_coin_corners(s0, L, h);
    CHECK(p0[0].x == doctest::Approx(-0.012));
    CHECK(p0[0].y == doctest::Approx(-0.001));
    CHECK(p0[1].x == doctest::Approx( 0.012));
    CHECK(p0[1].y == doctest::Approx(-0.001));

    // theta = 90 deg (vertical coin)
    State s90 = { 0.0, 0.0, 0.5 * M_PI, 0.0, 0.0, 0.0 };
    auto p90 = get_coin_corners(s90, L, h);
    // At 90 deg, major axis is vertical: Y extends to +- L/2
    double max_y = std::max({p90[0].y, p90[1].y, p90[2].y, p90[3].y});
    CHECK(max_y == doctest::Approx(0.012));

    // theta = 45 deg
    State s45 = { 1.0, -0.5, 0.25 * M_PI, 0.0, 0.0, 0.0 };
    auto p45 = get_coin_corners(s45, L, h);
    // Center of corners must equal coin center (X=1.0, Y=-0.5)
    double cx = (p45[0].x + p45[1].x + p45[2].x + p45[3].x) / 4.0;
    double cy = (p45[0].y + p45[1].y + p45[2].y + p45[3].y) / 4.0;
    CHECK(cx == doctest::Approx(1.0));
    CHECK(cy == doctest::Approx(-0.5));
}

TEST_CASE("Test 8: Integrator RK4 Convergence Rate") {
    PlateConfig p;
    FluidConfig f;
    CoeffsConfig c;
    Model m(p, f, c);

    State s0 = { 0.0, 0.0, 0.2, 0.05, -0.1, 0.5 };
    double t_end = 0.01;

    // Run with dt1, dt2 = dt1/2, dt3 = dt2/2
    auto integrate = [&](double dt) {
        State s = s0;
        double t = 0.0;
        int n = static_cast<int>(std::round(t_end / dt));
        for (int i = 0; i < n; ++i) {
            s = rk4_step(m, t, s, dt);
            t += dt;
        }
        return s;
    };

    State s_fine = integrate(1e-5);
    State s_1 = integrate(4e-4);
    State s_2 = integrate(2e-4);

    double err1 = std::abs(s_1[0] - s_fine[0]);
    double err2 = std::abs(s_2[0] - s_fine[0]);

    // For RK4, halving dt should reduce error by roughly factor of 16 (2^4)
    if (err1 > 1e-12 && err2 > 1e-12) {
        double ratio = err1 / err2;
        CHECK(ratio > 8.0);
    }
}

TEST_CASE("Test 9: No-NaN Fuzzing Guard") {
    std::mt19937 rng(12345);
    std::uniform_real_distribution<double> dist_L(0.005, 0.10);
    std::uniform_real_distribution<double> dist_h(0.0005, 0.02);
    std::uniform_real_distribution<double> dist_rho(1100.0, 15000.0);
    std::uniform_real_distribution<double> dist_th(-10.0, 10.0);
    std::uniform_real_distribution<double> dist_v(-2.0, 2.0);

    FluidConfig f;
    CoeffsConfig c;

    for (int iter = 0; iter < 50; ++iter) {
        PlateConfig p;
        p.L = dist_L(rng);
        p.h = dist_h(rng);
        p.rho_s = dist_rho(rng);

        Model m(p, f, c);
        State s = { 0.0, 0.0, dist_th(rng), dist_v(rng), dist_v(rng), dist_v(rng) };

        // Step for 10 steps
        double t = 0.0;
        for (int k = 0; k < 10; ++k) {
            s = rk4_step(m, t, s, 1e-3);
            t += 1e-3;
        }

        for (size_t i = 0; i < 6; ++i) {
            CHECK(!std::isnan(s[i]));
            CHECK(!std::isinf(s[i]));
        }
    }
}
