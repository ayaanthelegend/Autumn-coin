#pragma once

#include "config.hpp"
#include "fluid_state.hpp"
#include "kernels.hpp"
#include <vector>

namespace sph {

class RigidEllipse {
public:
    RigidPlateConfig config;
    int body_id = 0;

    // Kinematic & Dynamic State in Lab Frame
    Vec2 pos = {0.0, 0.0};
    Vec2 vel = {0.0, 0.0};
    Vec2 vel_half = {0.0, 0.0};
    Vec2 acc = {0.0, 0.0};
    Vec2 acc_prev = {0.0, 0.0};

    double theta = 0.0;
    double omega = 0.0;
    double omega_half = 0.0;
    double alpha = 0.0;
    double alpha_prev = 0.0;

    double mass = 0.0;
    double inertia = 0.0;
    int N_h = 2; // Particles across minor axis

    // Boundary particles attached to this rigid body
    std::vector<BoundaryParticle> particles;

    RigidEllipse() = default;
    explicit RigidEllipse(const RigidPlateConfig& cfg, int id = 0);

    void init_discretization(double dx, const WendlandC2Kernel& kernel);
    void update_particles(bool update_acc = true);
    void apply_force_and_torque(const Vec2& total_force, double total_torque, const Vec2& gravity);
};

} // namespace sph
