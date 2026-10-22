#pragma once

#include "config.hpp"
#include <vector>

namespace sph {

struct FluidParticle {
    Vec2 pos = {0.0, 0.0};
    Vec2 vel = {0.0, 0.0};
    Vec2 vel_half = {0.0, 0.0};
    Vec2 acc = {0.0, 0.0};
    double rho = 998.0;
    double p = 0.0;
    double mass = 0.0;
    double volume = 0.0;
    double vorticity = 0.0;
};

struct BoundaryParticle {
    Vec2 pos = {0.0, 0.0};
    Vec2 vel = {0.0, 0.0};
    Vec2 vel_half = {0.0, 0.0};
    Vec2 acc = {0.0, 0.0};
    Vec2 normal = {0.0, 0.0};
    double psi = 0.0; // Akinci boundary volume Psi_b = 1 / sum W_bk
    double p = 0.0;   // Extrapolated pressure
    int body_id = -1; // -1: fixed tank wall, >= 0: rigid body index
    Vec2 local_pos = {0.0, 0.0}; // Local coordinates in rigid body frame
};

} // namespace sph
