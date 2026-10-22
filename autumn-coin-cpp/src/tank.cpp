#include "autumn/tank.hpp"
#include <algorithm>

namespace autumn {

std::array<Vec2, 4> get_coin_corners(const State& s, double L, double h, double visual_exaggeration) {
    const double th = s[2];
    const double c = std::cos(th);
    const double sn = std::sin(th);

    const double eff_h = h * visual_exaggeration;
    const double lx[4] = {-0.5 * L,  0.5 * L, 0.5 * L, -0.5 * L};
    const double ly[4] = {-0.5 * eff_h, -0.5 * eff_h, 0.5 * eff_h,  0.5 * eff_h};

    std::array<Vec2, 4> p;
    for (int i = 0; i < 4; ++i) {
        p[i] = {
            s[0] + lx[i] * c - ly[i] * sn,
            s[1] + lx[i] * sn + ly[i] * c
        };
    }
    return p;
}

Outcome check_tank_contact(const State& s, double L, double h, const TankConfig& tank) {
    const auto p = get_coin_corners(s, L, h, 1.0); // check contact on true physical outline

    double min_y = p[0].y;
    double max_abs_x = std::abs(p[0].x);

    for (int i = 1; i < 4; ++i) {
        min_y = std::min(min_y, p[i].y);
        max_abs_x = std::max(max_abs_x, std::abs(p[i].x));
    }

    if (min_y <= -tank.water_height) {
        return Outcome::Bottom;
    }
    if (max_abs_x >= 0.5 * tank.width) {
        return Outcome::Wall;
    }

    return Outcome::Running;
}

} // namespace autumn
