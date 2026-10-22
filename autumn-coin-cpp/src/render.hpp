#pragma once

#include "autumn/types.hpp"
#include "autumn/tank.hpp"
#include "autumn/model.hpp"
#include <vector>

namespace autumn {

struct RenderSettings {
    double px_per_m = 1800.0;             // Scale factor (38 cm tank = ~684 px)
    Vec2 tank_origin_px = { 50.0, 50.0 };  // Screen position of top-left inside corner of water tank
    double thickness_exaggeration = 1.0;  // 1.0x to 5.0x visual thickness
    bool follow_camera = false;
    bool show_trail = true;
    bool show_ghosts = true;
    bool show_forces = false;
    int ghost_interval_ms = 80;
    int max_trail_points = 4000;
};

class TankRenderer {
public:
    TankRenderer() = default;

    Vec2 world_to_screen(double wx, double wy, const TankConfig& tank, const RenderSettings& settings) const;

    void draw(const TankConfig& tank,
              const Model& model,
              const State& current_state,
              const std::vector<Sample>& trail_samples,
              const std::vector<std::vector<Vec2>>& ghost_trajectories,
              const RenderSettings& settings,
              int viewport_w,
              int viewport_h);
};

} // namespace autumn
