#pragma once

#include "sph_solver.hpp"

namespace sph {

// Synchronous Kick-Drift-Kick integrator wrapper
inline void integrate_kdk(SPHSolver& solver, double dt) {
    solver.step_kdk(dt);
}

} // namespace sph
