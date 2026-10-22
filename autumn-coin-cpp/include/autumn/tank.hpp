#pragma once

#include "types.hpp"
#include <array>
#include <cmath>

namespace autumn {

struct TankConfig {
    double width = 0.38;          // 38 cm
    double water_height = 0.38;   // 38 cm
    double glass_thickness = 0.006; // 6 mm
};

// Four corners of the coin rectangle (chord L, thickness h), in lab frame (metres)
std::array<Vec2, 4> get_coin_corners(const State& s, double L, double h, double visual_exaggeration = 1.0);

// Check contact on rotated outline against floor and walls
Outcome check_tank_contact(const State& s, double L, double h, const TankConfig& tank);

} // namespace autumn
