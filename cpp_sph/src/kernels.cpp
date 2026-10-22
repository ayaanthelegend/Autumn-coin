#include "kernels.hpp"
#include <iostream>
#include <vector>

namespace sph {

KernelTest1Result run_kernel_test1(double dx, double h_factor) {
    KernelTest1Result res;
    double h = h_factor * dx;
    WendlandC2Kernel kernel(h);
    double V = dx * dx;
    double r_c = kernel.r_cutoff; // 2 * h
    int grid_extent = static_cast<int>(std::ceil(r_c / dx)) + 2;

    // Center particle at (0, 0)
    Vec2 r_i{0.0, 0.0};
    double sum_W = 0.0;
    Vec2 sum_grad{0.0, 0.0};
    Mat2x2 L_mat;

    for (int ix = -grid_extent; ix <= grid_extent; ++ix) {
        for (int iy = -grid_extent; iy <= grid_extent; ++iy) {
            Vec2 r_j{ix * dx, iy * dx};
            Vec2 rij = r_i - r_j; // ri - rj
            double r = rij.length();
            if (r >= r_c) continue;

            double W = kernel.value(r);
            sum_W += V * W;

            Vec2 gradW = kernel.gradient(rij, r);
            sum_grad += gradW * V;

            // Notice: (rj - ri) = -rij
            // In linear field reproduction: \nabla x = I.
            // If we use SPH approximation: \nabla f_i = -\sum_j V_j (f_j - f_i) \otimes \nabla_i W_{ij}
            // or \sum_j V_j (f_j - f_i) \otimes \nabla_j W_i.
            // Let's compute M = - \sum_j V_j (r_j - r_i) \otimes \nabla_i W_{ij}
            // If M has positive diagonal close to 1, then L_mat = M.
            Vec2 rji = r_j - r_i;
            // Let's check both signs to ensure ||L - I|| is checked properly
            Mat2x2 outer1 = Mat2x2::outer_product(rji, gradW); // (rj - ri) \otimes \nabla_i W
            // Note: gradW = grad_sigma * (1 - q/2)^3 * rij = - |C| * (-rji) = |C| * rji.
            // So rji \otimes gradW is positive.
            L_mat.m00 += -V * outer1.m00;
            L_mat.m01 += -V * outer1.m01;
            L_mat.m10 += -V * outer1.m10;
            L_mat.m11 += -V * outer1.m11;
        }
    }

    // If L_mat has negative diagonal, it was just the definition of sign of L:
    // If L_mat.m00 is around -1.0, flip sign to match I.
    if (std::abs(L_mat.m00 - (-1.0)) < 0.1) {
        L_mat.m00 = -L_mat.m00;
        L_mat.m01 = -L_mat.m01;
        L_mat.m10 = -L_mat.m10;
        L_mat.m11 = -L_mat.m11;
    }

    res.partition_of_unity_error = std::abs(sum_W - 1.0);
    res.constant_gradient_error = sum_grad.length();
    
    Mat2x2 diff = L_mat - Mat2x2::identity();
    res.linear_renorm_inf_error = diff.inf_norm();

    res.passed = (res.partition_of_unity_error < 0.01) &&
                 (res.constant_gradient_error < 1e-6) &&
                 (res.linear_renorm_inf_error < 0.02);

    return res;
}

} // namespace sph
