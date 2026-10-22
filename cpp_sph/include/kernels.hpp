#pragma once

#include "config.hpp"
#include <cmath>

namespace sph {

// 2D Wendland C2 Kernel
// W(r, h) = (7 / (4 * pi * h^2)) * (1 - q/2)^4 * (2q + 1) for q = r / h in [0, 2)
// Grad_i W(rij, h) = - (35 / (4 * pi * h^4)) * (1 - q/2)^3 * (ri - rj)
class WendlandC2Kernel {
public:
    double h;
    double h_sq;
    double h_cube;
    double h_fourth;
    double r_cutoff;
    double sigma;      // 7 / (4 * pi * h^2)
    double grad_sigma; // -35 / (4 * pi * h^4)

    explicit WendlandC2Kernel(double h_sml = 0.0013) {
        set_h(h_sml);
    }

    void set_h(double h_sml) {
        h = h_sml;
        h_sq = h * h;
        h_cube = h_sq * h;
        h_fourth = h_sq * h_sq;
        r_cutoff = 2.0 * h;
        sigma = 7.0 / (4.0 * M_PI * h_sq);
        grad_sigma = -35.0 / (4.0 * M_PI * h_fourth);
    }

    // Value W(r, h)
    double value(double r) const {
        if (r >= r_cutoff || r < 0.0) return 0.0;
        double q = r / h;
        double term = 1.0 - 0.5 * q;
        double term4 = term * term * term * term;
        return sigma * term4 * (2.0 * q + 1.0);
    }

    // Gradient grad_i W(ri - rj) = grad_sigma * (1 - q/2)^3 * (ri - rj)
    // Note: points away from rj towards ri when rij = ri - rj.
    // If r >= r_cutoff or r < 1e-12, returns {0, 0}.
    Vec2 gradient(const Vec2& rij, double r) const {
        if (r >= r_cutoff || r < 1e-12) {
            return {0.0, 0.0};
        }
        double q = r / h;
        double term = 1.0 - 0.5 * q;
        double term3 = term * term * term;
        double factor = grad_sigma * term3;
        return rij * factor;
    }

    Vec2 gradient(const Vec2& rij) const {
        double r = rij.length();
        return gradient(rij, r);
    }
};

// Verification functions for Test 1
struct KernelTest1Result {
    double partition_of_unity_error = 0.0;
    double constant_gradient_error = 0.0;
    double linear_renorm_inf_error = 0.0;
    bool passed = false;
};

KernelTest1Result run_kernel_test1(double dx = 0.001, double h_factor = 1.3);

} // namespace sph
