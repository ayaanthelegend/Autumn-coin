#include "autumn/types.hpp"
#include "autumn/model.hpp"
#include "autumn/tank.hpp"
#include "autumn/config.hpp"
#include "autumn/regime.hpp"
#include "autumn/sweep.hpp"
#include "render.hpp"
#include "plots.hpp"
#include "ui.hpp"

#include "raylib.h"
#include "rlImGui.h"
#include "imgui.h"
#include "implot.h"

#include <iostream>
#include <vector>
#include <string>
#include <filesystem>
#include <cmath>
#include <algorithm>

namespace fs = std::filesystem;

static std::string find_config_dir(const std::string& user_dir) {
    if (!user_dir.empty() && fs::exists(user_dir)) return user_dir;
    std::vector<std::string> candidates = {
        "autumn-coin-cpp/config",
        "config",
        "../config",
        "../../config"
    };
    for (const auto& c : candidates) {
        if (fs::exists(c) && fs::exists(c + "/base.yaml") && fs::exists(c + "/coins.yaml")) {
            return c;
        }
    }
    for (const auto& c : candidates) {
        if (fs::exists(c) && fs::exists(c + "/base.yaml")) {
            return c;
        }
    }
    return "autumn-coin-cpp/config";
}

int main(int argc, char* argv[]) {
    // 1. CLI Arguments Parsing
    std::string config_dir = "";
    std::string coin_id = "reference_card";
    double theta0_deg = 45.0;
    double time_scale = 0.3; // Default 0.3x slow-motion
    bool headless = false;
    std::string out_csv = "";
    std::string sweep_arg = "";
    int max_frames = 0;
    std::string screenshot_path = "";

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--config" && i + 1 < argc) {
            config_dir = argv[++i];
        } else if (arg == "--coin" && i + 1 < argc) {
            coin_id = argv[++i];
        } else if (arg == "--theta" && i + 1 < argc) {
            theta0_deg = std::stod(argv[++i]);
        } else if (arg == "--timescale" && i + 1 < argc) {
            time_scale = std::stod(argv[++i]);
        } else if (arg == "--headless") {
            headless = true;
        } else if (arg == "--out" && i + 1 < argc) {
            out_csv = argv[++i];
        } else if (arg == "--sweep" && i + 1 < argc) {
            sweep_arg = argv[++i];
        } else if (arg == "--frames" && i + 1 < argc) {
            max_frames = std::stoi(argv[++i]);
        } else if (arg == "--screenshot" && i + 1 < argc) {
            screenshot_path = argv[++i];
        }
    }

    config_dir = find_config_dir(config_dir);

    // 2. Load configurations
    autumn::FluidConfig fluid;
    autumn::CoeffsConfig coeffs;
    autumn::RegimeClassifierConfig classifier;
    autumn::TankConfig tank;

    autumn::load_base_config(config_dir + "/base.yaml", fluid, coeffs, classifier);
    const autumn::CoeffsConfig default_coeffs = coeffs;

    std::vector<autumn::PlateConfig> all_coins = autumn::load_coin_sets(config_dir + "/coin_sets.yaml");
    std::vector<autumn::PlateConfig> pk_coins = autumn::load_coins_yaml(config_dir + "/coins.yaml");
    all_coins.insert(all_coins.end(), pk_coins.begin(), pk_coins.end());

    int selected_idx = 0;
    for (size_t i = 0; i < all_coins.size(); ++i) {
        if (all_coins[i].id == coin_id) {
            selected_idx = (int)i;
            break;
        }
    }

    autumn::PlateConfig current_plate = all_coins.empty() ? autumn::PlateConfig{} : all_coins[selected_idx];

    // 3. Headless Execution Mode
    if (headless) {
        std::cout << "[Headless] Running coin: " << current_plate.label
                  << " at theta0 = " << theta0_deg << " deg\n";
        autumn::Model model(current_plate, fluid, coeffs);
        autumn::SimulationRun run(model, tank, theta0_deg, 1e-6);

        while (!run.finished()) {
            run.advance(0.1, 1e-4, 0.001, 25.0);
        }

        autumn::Regime reg = autumn::classify_regime(run.samples(), tank.water_height, classifier);
        std::cout << "[Headless] Outcome: " << (int)run.outcome()
                  << " | Regime: " << autumn::regime_to_string(reg)
                  << " | Time: " << run.current_time() << " s\n";

        if (!out_csv.empty()) {
            if (autumn::export_trajectory_csv(out_csv, run.samples())) {
                std::cout << "[Headless] Exported trajectory to: " << out_csv << "\n";
            } else {
                std::cerr << "[Headless] Failed to export CSV: " << out_csv << "\n";
            }
        }
        return 0;
    }

    // 4. GUI Window Mode (raylib + Dear ImGui + ImPlot)
    const int screen_width = 1600;
    const int screen_height = 900;

    SetConfigFlags(FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT | FLAG_MSAA_4X_HINT);
    InitWindow(screen_width, screen_height, "Autumn Coin - 2D Falling Plate ODE Visualizer");
    SetTargetFPS(60);

    // Setup rlImGui (light theme: false)
    rlImGuiSetup(false);
    ImGui::GetIO().IniFilename = nullptr; // Prevent imgui.ini from overriding layout
    ImPlot::CreateContext();

    autumn::TankRenderer renderer;
    autumn::RenderSettings render_settings;
    render_settings.px_per_m = 1500.0;
    render_settings.tank_origin_px = { 75.0, 70.0 };

    autumn::LivePlotPanel plot_panel;
    autumn::PlotData plot_data;
    autumn::UIController ui_controller;

    autumn::UIState ui;
    ui.selected_coin_idx = selected_idx;
    ui.theta0_deg = theta0_deg;
    ui.time_scale = time_scale;

    autumn::Model model(current_plate, fluid, coeffs);
    autumn::SimulationRun run(model, tank, ui.theta0_deg, ui.perturb_rad);

    size_t last_plotted_sample = 0;
    double sim_time_budget = 0.0;
    const double dt_phys = 1e-4;
    int frame_counter = 0;

    while (!WindowShouldClose()) {
        float frame_dt = GetFrameTime();
        if (frame_dt > 0.1f) frame_dt = 0.1f; // Clamp large delta

        int cur_w = GetScreenWidth();
        int cur_h = GetScreenHeight();

        // Check if model needs rebuild (plate or fluid or coeffs changed)
        if (ui.reset_requested) {
            current_plate = all_coins[ui.selected_coin_idx];
            model = autumn::Model(current_plate, fluid, coeffs);
            if (plot_data.compare_previous) {
                plot_data.archive_run(run.samples());
            }
            run.reset(ui.theta0_deg, ui.perturb_rad);
            plot_data.clear();
            last_plotted_sample = 0;
            ui.reset_requested = false;
        }

        // Advance simulation physics
        if (!ui.is_paused && !run.finished()) {
            sim_time_budget += frame_dt * ui.time_scale;
            int sub_step_count = 0;
            const int max_sub_steps = 3000;

            while (sim_time_budget >= dt_phys && sub_step_count < max_sub_steps) {
                run.advance(dt_phys, dt_phys, 0.001, 25.0);
                sim_time_budget -= dt_phys;
                sub_step_count++;
                if (run.finished()) break;
            }
            if (sim_time_budget > dt_phys * 10) sim_time_budget = 0.0; // Prevent runaway
        } else if (ui.single_step_requested) {
            run.advance(0.016, dt_phys, 0.001, 25.0);
            ui.single_step_requested = false;
        }

        // Stream new samples to ring buffers
        const auto& samples = run.samples();
        while (last_plotted_sample < samples.size()) {
            plot_data.add_sample(samples[last_plotted_sample]);
            last_plotted_sample++;
        }

        autumn::Regime current_regime = autumn::classify_regime(samples, tank.water_height, classifier);

        // Prepare ghost trajectories for visualizer
        std::vector<std::vector<autumn::Vec2>> ghost_trajectories;
        for (const auto& row : ui.sweep_results) {
            if (!row.trajectory.empty()) {
                ghost_trajectories.push_back(row.trajectory);
            }
        }

        // Handle CSV Export
        if (ui.export_csv_requested) {
            std::string fn = "run_" + current_plate.id + "_th" + std::to_string((int)std::round(ui.theta0_deg)) + ".csv";
            if (autumn::export_trajectory_csv(fn, samples)) {
                ui.status_message = "Exported trajectory to " + fn;
            } else {
                ui.status_message = "Failed to export trajectory to " + fn;
            }
            ui.export_csv_requested = false;
        }

        // Handle Screenshot
        if (ui.screenshot_requested) {
            fs::create_directories("docs/screenshots");
            std::string sc_fn = "docs/screenshots/screenshot_" + current_plate.id + ".png";
            Image img = LoadImageFromScreen();
            ExportImage(img, sc_fn.c_str());
            UnloadImage(img);
            ui.status_message = "Saved screenshot to " + sc_fn;
            ui.screenshot_requested = false;
        }

        // Render Frame
        BeginDrawing();
        ClearBackground(WHITE);

        // 1. Draw 2D Glass Tank & Coin (Left side of screen)
        renderer.draw(tank, model, run.current_state(), samples, ghost_trajectories,
                      render_settings, cur_w, cur_h);

        // 2. Dear ImGui & ImPlot Panels (Strictly to the right of the glass water tank)
        rlImGuiBegin();

        float tank_reserved_width = (float)(tank.width * render_settings.px_per_m + 115.0); // ~685 px
        float avail_ui_width = (float)cur_w - tank_reserved_width - 25.0f;
        if (avail_ui_width < 640.0f) avail_ui_width = 640.0f;

        float controls_width = 390.0f;
        float plots_width = avail_ui_width - controls_width - 15.0f;
        if (plots_width < 360.0f) plots_width = 360.0f;

        float plots_x = tank_reserved_width + 10.0f;
        float side_panel_x = plots_x + plots_width + 12.0f;
        float status_h = 34.0f;
        float panel_h = (float)cur_h - status_h - 20.0f;

        // Live Plots Window between tank and controls (Middle Column)
        ImGui::SetNextWindowPos(ImVec2(plots_x, 10.0f), ImGuiCond_Always);
        ImGui::SetNextWindowSize(ImVec2(plots_width, panel_h), ImGuiCond_Always);
        ImGui::Begin("Live Plots", nullptr, ImGuiWindowFlags_NoCollapse);
        plot_panel.render(plot_data, plots_width - 15.0f, panel_h - 40.0f);
        ImGui::End();

        // Controls Window on far right (Right Column)
        ui_controller.render_controls(ui, render_settings, current_plate, all_coins,
                                     fluid, coeffs, default_coeffs, tank, classifier,
                                     plot_data, run.current_time(), run.current_state(),
                                     current_regime, run.outcome(),
                                     side_panel_x, 10.0f, controls_width, panel_h);

        // Status bar across full bottom
        ui_controller.render_status_bar(current_plate, fluid, run.current_time(),
                                       run.current_state(), current_regime, run.outcome(),
                                       (float)cur_w, status_h);

        rlImGuiEnd();
        EndDrawing();

        frame_counter++;
        if (max_frames > 0 && frame_counter >= max_frames) {
            if (!screenshot_path.empty()) {
                fs::create_directories(fs::path(screenshot_path).parent_path());
                Image img = LoadImageFromScreen();
                ExportImage(img, screenshot_path.c_str());
                UnloadImage(img);
                std::cout << "[Screenshot] Captured frame " << frame_counter << " to " << screenshot_path << "\n";
            }
            break;
        }
    }

    // Cleanup
    ImPlot::DestroyContext();
    rlImGuiShutdown();
    CloseWindow();

    return 0;
}
