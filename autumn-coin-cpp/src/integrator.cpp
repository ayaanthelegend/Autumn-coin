#include "autumn/integrator.hpp"
#include <cmath>
#include <algorithm>

namespace autumn {

State rk4_step(const Model& model, double t, const State& y, double dt) {
    auto add = [](const State& a, const State& b, double s) {
        State r;
        for (size_t i = 0; i < 6; ++i) r[i] = a[i] + s * b[i];
        return r;
    };

    const State k1 = model.rhs(t, y);
    const State k2 = model.rhs(t + 0.5 * dt, add(y, k1, 0.5 * dt));
    const State k3 = model.rhs(t + 0.5 * dt, add(y, k2, 0.5 * dt));
    const State k4 = model.rhs(t + dt, add(y, k3, dt));

    State r;
    for (size_t i = 0; i < 6; ++i) {
        r[i] = y[i] + (dt / 6.0) * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]);
    }
    return r;
}

bool rk45_step(const Model& model, double& t, State& y, double& dt, double rtol, double atol) {
    // Dormand-Prince Butcher tableau
    const State k1 = model.rhs(t, y);

    auto add2 = [](const State& y0, const State& k1, double b1, double dt) {
        State r; for (size_t i = 0; i < 6; ++i) r[i] = y0[i] + dt * (b1 * k1[i]); return r;
    };
    const State k2 = model.rhs(t + (1.0/5.0)*dt, add2(y, k1, 1.0/5.0, dt));

    auto add3 = [](const State& y0, const State& k1, double b1, const State& k2, double b2, double dt) {
        State r; for (size_t i = 0; i < 6; ++i) r[i] = y0[i] + dt * (b1 * k1[i] + b2 * k2[i]); return r;
    };
    const State k3 = model.rhs(t + (3.0/10.0)*dt, add3(y, k1, 3.0/40.0, k2, 9.0/40.0, dt));

    auto add4 = [](const State& y0, const State& k1, double b1, const State& k2, double b2, const State& k3, double b3, double dt) {
        State r; for (size_t i = 0; i < 6; ++i) r[i] = y0[i] + dt * (b1 * k1[i] + b2 * k2[i] + b3 * k3[i]); return r;
    };
    const State k4 = model.rhs(t + (4.0/5.0)*dt, add4(y, k1, 44.0/45.0, k2, -56.0/15.0, k3, 32.0/9.0, dt));

    auto add5 = [](const State& y0, const State& k1, double b1, const State& k2, double b2, const State& k3, double b3, const State& k4, double b4, double dt) {
        State r; for (size_t i = 0; i < 6; ++i) r[i] = y0[i] + dt * (b1 * k1[i] + b2 * k2[i] + b3 * k3[i] + b4 * k4[i]); return r;
    };
    const State k5 = model.rhs(t + (8.0/9.0)*dt, add5(y, k1, 19372.0/6561.0, k2, -25360.0/2187.0, k3, 64448.0/6561.0, k4, -212.0/729.0, dt));

    auto add6 = [](const State& y0, const State& k1, double b1, const State& k2, double b2, const State& k3, double b3, const State& k4, double b4, const State& k5, double b5, double dt) {
        State r; for (size_t i = 0; i < 6; ++i) r[i] = y0[i] + dt * (b1 * k1[i] + b2 * k2[i] + b3 * k3[i] + b4 * k4[i] + b5 * k5[i]); return r;
    };
    const State k6 = model.rhs(t + dt, add6(y, k1, 9017.0/3168.0, k2, -355.0/33.0, k3, 46732.0/5247.0, k4, 49.0/176.0, k5, -5103.0/18656.0, dt));

    // 5th order solution
    State y5;
    for (size_t i = 0; i < 6; ++i) {
        y5[i] = y[i] + dt * (35.0/384.0 * k1[i] + 500.0/1113.0 * k3[i] + 125.0/192.0 * k4[i] - 2187.0/6784.0 * k5[i] + 11.0/84.0 * k6[i]);
    }

    // 4th order solution for error estimation
    const State k7 = model.rhs(t + dt, y5);
    State y4;
    for (size_t i = 0; i < 6; ++i) {
        y4[i] = y[i] + dt * (5179.0/57600.0 * k1[i] + 7571.0/16695.0 * k3[i] + 393.0/640.0 * k4[i] - 92097.0/339200.0 * k5[i] + 187.0/2100.0 * k6[i] + 1.0/40.0 * k7[i]);
    }

    // Error norm
    double max_err = 0.0;
    for (size_t i = 0; i < 6; ++i) {
        const double sc = atol + rtol * std::max(std::abs(y[i]), std::abs(y5[i]));
        const double err = std::abs(y5[i] - y4[i]) / sc;
        max_err = std::max(max_err, err);
    }

    if (max_err <= 1.0) {
        t += dt;
        y = y5;
        // adapt dt up
        const double factor = std::min(5.0, std::max(0.2, 0.9 * std::pow(max_err, -0.2)));
        dt *= factor;
        return true;
    } else {
        // adapt dt down and retry
        const double factor = std::max(0.1, 0.9 * std::pow(max_err, -0.25));
        dt *= factor;
        return false;
    }
}

} // namespace autumn
