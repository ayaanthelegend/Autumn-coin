#pragma once

#include "autumn/types.hpp"
#include "autumn/model.hpp"
#include "autumn/tank.hpp"
#include "autumn/regime.hpp"
#include "autumn/sweep.hpp"
#include "render.hpp"
#include "plots.hpp"
#include <vector>
#include <string>
#include <functional>

namespace autumn {

struct UIState {
    int selected_coin_idx = 0;
    double theta0_deg = 45.0;
    double perturb_rad = 1e-6;
    double time_scale = 1.0;
    bool is_paused = false;
    bool single_step_requested = false;
    bool reset_requested = false;

    // Angle sweep
    double sweep_min_deg = 0.0;
    double sweep_max_deg = 360.0;
    double sweep_step_deg = 15.0;
    bool sweep_running = false;
    std::vector<SweepRow> sweep_results;

    // Screenshot & CSV flags
    bool export_csv_requested = false;
    bool screenshot_requested = false;
    std::string status_message = "";
};

class UIController {
public:
    UIController();

    void setup_light_theme();

    void render_controls(UIState& ui,
                         RenderSettings& render_settings,
                         PlateConfig& current_plate,
                         const std::vector<PlateConfig>& available_coins,
                         FluidConfig& fluid,
                         CoeffsConfig& coeffs,
                         const CoeffsConfig& default_coeffs,
                         TankConfig& tank,
                         const RegimeClassifierConfig& classifier,
                         PlotData& plot_data,
                         double current_time,
                         const State& current_state,
                         Regime current_regime,
                         Outcome current_outcome,
                         float pos_x,
                         float pos_y,
                         float panel_width,
                         float panel_height);

    void render_status_bar(const PlateConfig& plate,
                           const FluidConfig& fluid,
                           double current_time,
                           const State& current_state,
                           Regime current_regime,
                           Outcome current_outcome,
                           float screen_width,
                           float bar_height);

private:
    bool theme_initialized_ = false;
};

} // namespace autumn
