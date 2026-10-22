#include "doctest.h"
#include "autumn/model.hpp"
#include "autumn/integrator.hpp"
#include <cmath>

using namespace autumn;

TEST_CASE("Test 4: Mechanical Energy Conservation (Inviscid / Non-Dissipative)") {
    PlateConfig p;
    p.L = 0.024;
    p.h = 0.0018;
    p.rho_s = 7800.0;

    FluidConfig f;
    f.rho_f = 998.0;
    f.g = 9.81;

    // Switch off all dissipative forces and circulation
    CoeffsConfig c;
    c.C_T = 0.0;
    c.C_R = 0.0;
    c.C_D0 = 0.0;
    c.C_D1 = 0.0;
    c.C_tau = 0.0;
    c.c_lin = 0.0;
    c.mu_1 = 0.0;

    Model m(p, f, c);

    // Initial state: released with initial angle and small velocity
    State s = { 0.0, 0.0, 0.45, 0.1, -0.05, 1.2 };
    const double E0 = m.total_energy(s);

    double dt = 1e-4;
    double t = 0.0;
    double max_rel_err = 0.0;

    for (int step = 0; step < 2000; ++step) {
        s = rk4_step(m, t, s, dt);
        t += dt;
        double E = m.total_energy(s);
        double rel_err = std::abs(E - E0) / (std::abs(E0) + 1e-6);
        max_rel_err = std::max(max_rel_err, rel_err);
    }

    // Energy should be conserved to integrator precision (< 1e-6)
    CHECK(max_rel_err < 1e-6);
}
