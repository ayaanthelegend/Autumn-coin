#include "rigid_ellipse.hpp"
#include <cmath>
#include <iostream>

namespace sph {

RigidEllipse::RigidEllipse(const RigidPlateConfig& cfg, int id)
    : config(cfg), body_id(id), pos(cfg.pos), vel(cfg.vel), vel_half(cfg.vel),
      theta(cfg.theta), omega(cfg.omega), omega_half(cfg.omega) {
    mass = cfg.mass();
    inertia = cfg.inertia();
}

void RigidEllipse::init_discretization(double dx, const WendlandC2Kernel& kernel) {
    particles.clear();
    double a = config.a();
    double b = config.b();
    N_h = std::max(1, static_cast<int>(std::round(config.h / dx)));

    int nx = static_cast<int>(std::ceil(a / dx));
    int ny = static_cast<int>(std::ceil(b / dx));

    // Place boundary particles along perimeter and surface shell (Akinci et al. 2012)
    for (int iy = -ny; iy <= ny; ++iy) {
        double y = iy * dx;
        for (int ix = -nx; ix <= nx; ++ix) {
            double x = ix * dx;
            double ellipse_val = (x * x) / (a * a) + (y * y) / (b * b);
            if (ellipse_val <= 1.0) {
                // If body is thin (b <= 2*dx), include all points;
                // Otherwise include surface boundary shell points
                bool is_surface = (b <= 2.0 * dx) || (ellipse_val >= 0.35);
                if (is_surface) {
                    BoundaryParticle bp;
                    bp.local_pos = {x, y};
                    bp.body_id = body_id;
                    double nx_norm = (a > 1e-12) ? (x / (a * a)) : 0.0;
                    double ny_norm = (b > 1e-12) ? (y / (b * b)) : 0.0;
                    Vec2 norm_vec{nx_norm, ny_norm};
                    bp.normal = norm_vec.normalized();
                    particles.push_back(bp);
                }
            }
        }
    }

    if (particles.empty()) {
        // Fallback: at least one particle at center
        BoundaryParticle bp;
        bp.local_pos = {0.0, 0.0};
        bp.body_id = body_id;
        bp.normal = {0.0, 1.0};
        particles.push_back(bp);
    }

    // Compute Akinci boundary volume Psi_b = 1 / sum W_bk
    double default_vol = dx * dx;
    for (size_t b_idx = 0; b_idx < particles.size(); ++b_idx) {
        double sum_W = 0.0;
        for (size_t k_idx = 0; k_idx < particles.size(); ++k_idx) {
            Vec2 diff = particles[b_idx].local_pos - particles[k_idx].local_pos;
            sum_W += kernel.value(diff.length());
        }
        if (sum_W > 1e-6) {
            particles[b_idx].psi = 1.0 / sum_W;
        } else {
            particles[b_idx].psi = default_vol;
        }
    }

    // Normalize boundary volumes so that sum Psi_b matches exact geometric area
    double sum_psi = 0.0;
    for (const auto& bp : particles) {
        sum_psi += bp.psi;
    }
    double exact_area = config.area();
    if (sum_psi > 1e-12) {
        double scale = exact_area / sum_psi;
        for (auto& bp : particles) {
            bp.psi *= scale;
        }
    }

    update_particles(false);
}

void RigidEllipse::update_particles(bool update_acc) {
    double cos_th = std::cos(theta);
    double sin_th = std::sin(theta);

    for (auto& bp : particles) {
        // Transform local position to lab frame
        double lx = bp.local_pos.x;
        double ly = bp.local_pos.y;
        double gx = pos.x + (cos_th * lx - sin_th * ly);
        double gy = pos.y + (sin_th * lx + cos_th * ly);
        bp.pos = {gx, gy};

        // Linear velocity v_b = V + omega x (r_b - R)
        // In 2D: omega x r = {-omega * r_y, omega * r_x}
        double rx = gx - pos.x;
        double ry = gy - pos.y;
        bp.vel = {vel.x - omega * ry, vel.y + omega * rx};
        bp.vel_half = {vel_half.x - omega_half * ry, vel_half.y + omega_half * rx};

        if (update_acc) {
            // Acceleration a_b = A + alpha x r + omega x (omega x r)
            // = A + {-alpha * ry - omega^2 * rx, alpha * rx - omega^2 * ry}
            double omega_sq = omega * omega;
            bp.acc = {acc.x - alpha * ry - omega_sq * rx,
                      acc.y + alpha * rx - omega_sq * ry};
        }
    }
}

void RigidEllipse::apply_force_and_torque(const Vec2& total_force, double total_torque, const Vec2& gravity) {
    if (config.fixed) {
        acc = {0.0, 0.0};
        alpha = 0.0;
        vel = {0.0, 0.0};
        vel_half = {0.0, 0.0};
        omega = 0.0;
        omega_half = 0.0;
        return;
    }

    acc_prev = acc;
    alpha_prev = alpha;

    Vec2 f_gravity = gravity * mass;
    Vec2 f_net = total_force + f_gravity;

    acc = (mass > 1e-12) ? (f_net / mass) : Vec2{0.0, 0.0};
    alpha = (inertia > 1e-12) ? (total_torque / inertia) : 0.0;
}

} // namespace sph
