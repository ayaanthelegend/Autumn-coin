#pragma once

#include "model.hpp"

namespace autumn {

State rk4_step(const Model& model, double t, const State& y, double dt);

// Adaptive RK45 (Dormand-Prince) step
bool rk45_step(const Model& model, double& t, State& y, double& dt, double rtol = 1e-7, double atol = 1e-9);

} // namespace autumn
