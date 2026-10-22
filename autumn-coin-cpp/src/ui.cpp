#include "ui.hpp"
#include "imgui.h"
#include <cmath>
#include <iomanip>
#include <sstream>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace autumn {

UIController::UIController() {}

void UIController::setup_light_theme() {
    ImGui::StyleColorsLight();
    ImGuiStyle& style = ImGui::GetStyle();

    style.WindowRounding = 6.0f;
    style.FrameRounding = 4.0f;
    style.PopupRounding = 4.0f;
    style.ScrollbarRounding = 4.0f;
    style.GrabRounding = 4.0f;
    style.TabRounding = 4.0f;
    style.FrameBorderSize = 1.0f;

    ImVec4* colors = style.Colors;
    colors[ImGuiCol_Text]                  = ImVec4(0.08f, 0.10f, 0.12f, 1.0f);
    colors[ImGuiCol_TextDisabled]          = ImVec4(0.50f, 0.55f, 0.60f, 1.0f);
    colors[ImGuiCol_WindowBg]              = ImVec4(1.0f, 1.0f, 1.0f, 0.98f);
    colors[ImGuiCol_ChildBg]               = ImVec4(0.97f, 0.98f, 0.99f, 1.0f);
    colors[ImGuiCol_PopupBg]               = ImVec4(1.0f, 1.0f, 1.0f, 0.98f);
    colors[ImGuiCol_Border]                = ImVec4(0.78f, 0.82f, 0.86f, 1.0f);
    colors[ImGuiCol_BorderShadow]          = ImVec4(0.00f, 0.00f, 0.00f, 0.00f);
    colors[ImGuiCol_FrameBg]               = ImVec4(1.00f, 1.00f, 1.00f, 1.0f);
    colors[ImGuiCol_FrameBgHovered]        = ImVec4(0.90f, 0.94f, 0.98f, 1.0f);
    colors[ImGuiCol_FrameBgActive]         = ImVec4(0.85f, 0.90f, 0.95f, 1.0f);
    colors[ImGuiCol_TitleBg]               = ImVec4(0.92f, 0.94f, 0.96f, 1.0f);
    colors[ImGuiCol_TitleBgActive]         = ImVec4(0.85f, 0.90f, 0.95f, 1.0f);
    colors[ImGuiCol_MenuBarBg]             = ImVec4(0.94f, 0.96f, 0.98f, 1.0f);
    colors[ImGuiCol_ScrollbarBg]           = ImVec4(0.95f, 0.95f, 0.95f, 0.5f);
    colors[ImGuiCol_ScrollbarGrab]         = ImVec4(0.70f, 0.75f, 0.80f, 0.8f);
    colors[ImGuiCol_ScrollbarGrabHovered]  = ImVec4(0.60f, 0.65f, 0.70f, 0.9f);
    colors[ImGuiCol_ScrollbarGrabActive]   = ImVec4(0.45f, 0.50f, 0.55f, 1.0f);
    colors[ImGuiCol_CheckMark]             = ImVec4(0.15f, 0.45f, 0.85f, 1.0f);
    colors[ImGuiCol_SliderGrab]            = ImVec4(0.18f, 0.48f, 0.85f, 1.0f);
    colors[ImGuiCol_SliderGrabActive]      = ImVec4(0.12f, 0.38f, 0.75f, 1.0f);
    colors[ImGuiCol_Button]                = ImVec4(0.20f, 0.48f, 0.82f, 0.85f);
    colors[ImGuiCol_ButtonHovered]         = ImVec4(0.26f, 0.56f, 0.92f, 1.0f);
    colors[ImGuiCol_ButtonActive]          = ImVec4(0.15f, 0.40f, 0.75f, 1.0f);
    colors[ImGuiCol_Header]                = ImVec4(0.88f, 0.92f, 0.96f, 1.0f);
    colors[ImGuiCol_HeaderHovered]         = ImVec4(0.82f, 0.88f, 0.94f, 1.0f);
    colors[ImGuiCol_HeaderActive]          = ImVec4(0.76f, 0.82f, 0.90f, 1.0f);
    colors[ImGuiCol_Tab]                   = ImVec4(0.90f, 0.92f, 0.94f, 1.0f);
    colors[ImGuiCol_TabHovered]            = ImVec4(0.80f, 0.86f, 0.92f, 1.0f);
    colors[ImGuiCol_TabActive]             = ImVec4(0.98f, 0.99f, 1.00f, 1.0f);
}

void UIController::render_controls(UIState& ui,
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
                                   float panel_height) {
    if (!theme_initialized_) {
        setup_light_theme();
        theme_initialized_ = true;
    }

    ImGui::SetNextWindowPos(ImVec2(pos_x, pos_y), ImGuiCond_Always);
    ImGui::SetNextWindowSize(ImVec2(panel_width, panel_height), ImGuiCond_Always);

    ImGui::Begin("Autumn Coin Controls", nullptr, ImGuiWindowFlags_NoCollapse);

    // 1. Coin / Card Selection
    if (ImGui::CollapsingHeader("Coin & Parameter Set", ImGuiTreeNodeFlags_DefaultOpen)) {
        if (!available_coins.empty()) {
            std::string preview = available_coins[ui.selected_coin_idx].label;
            if (ImGui::BeginCombo("Select Coin", preview.c_str())) {
                for (int i = 0; i < (int)available_coins.size(); ++i) {
                    const auto& coin = available_coins[i];
                    bool is_selected = (ui.selected_coin_idx == i);

                    std::string item_text = coin.label;
                    if (!coin.enabled) {
                        item_text += " [Disabled: Needs Thickness]";
                    } else if (coin.source == "illustrative") {
                        item_text += " [Illustrative]";
                    }

                    if (!coin.enabled) {
                        ImGui::BeginDisabled();
                    }

                    if (ImGui::Selectable(item_text.c_str(), is_selected)) {
                        ui.selected_coin_idx = i;
                        current_plate = coin;
                        ui.reset_requested = true;
                    }

                    if (is_selected) {
                        ImGui::SetItemDefaultFocus();
                    }

                    if (!coin.enabled) {
                        ImGui::EndDisabled();
                    }
                }
                ImGui::EndCombo();
            }
        }

        // Display Coin Derived Properties
        double rho_eff = current_plate.effective_rho_s();
        double I_star = current_plate.I_star(fluid.rho_f);
        double U_t = current_plate.U_t(fluid.rho_f, fluid.g);

        ImGui::Text("Diameter L: %.1f mm | Thickness h: %.2f mm", current_plate.L * 1e3, current_plate.h * 1e3);
        ImGui::Text("Effective Density: %.0f kg/m^3 (Displaced ratio: %.2f)", rho_eff, rho_eff / fluid.rho_f);
        ImGui::Text("Moment of Inertia I*: %.3f | Char Speed U_t: %.2f m/s", I_star, U_t);

        if (current_plate.source == "illustrative") {
            ImGui::TextColored(ImVec4(0.8f, 0.45f, 0.1f, 1.0f), "* Illustrative preset (not measured coin)");
        }
    }

    ImGui::Separator();

    // 2. Release Angle Control
    if (ImGui::CollapsingHeader("Release Angle (theta0)", ImGuiTreeNodeFlags_DefaultOpen)) {
        float th = (float)ui.theta0_deg;
        if (ImGui::SliderFloat("Angle theta0 [deg]", &th, 0.0f, 360.0f, "%.1f deg")) {
            ui.theta0_deg = th;
            ui.reset_requested = true;
        }

        // Quick angle presets
        ImGui::Text("Quick Angles:");
        ImGui::SameLine();
        const double quick_angles[] = { 0.0, 30.0, 45.0, 60.0, 90.0, 135.0, 180.0 };
        for (double qa : quick_angles) {
            char btn_lbl[16];
            snprintf(btn_lbl, sizeof(btn_lbl), "%.0f°", qa);
            if (ImGui::Button(btn_lbl)) {
                ui.theta0_deg = qa;
                ui.reset_requested = true;
            }
            ImGui::SameLine();
        }
        ImGui::NewLine();

        // Release perturbation
        float pert = (float)ui.perturb_rad;
        if (ImGui::InputFloat("Perturbation [rad]", &pert, 1e-7f, 1e-5f, "%.1e")) {
            ui.perturb_rad = (double)pert;
        }
        ImGui::TextDisabled("Perturbation triggers flutter/tumble on exact symmetries (0°, 90°, 180°)");
    }

    ImGui::Separator();

    // 3. Simulation Controls
    if (ImGui::CollapsingHeader("Simulation Controls", ImGuiTreeNodeFlags_DefaultOpen)) {
        if (ui.is_paused) {
            if (ImGui::Button(" Play ", ImVec2(70.0f, 26.0f))) {
                ui.is_paused = false;
            }
        } else {
            if (ImGui::Button(" Pause ", ImVec2(70.0f, 26.0f))) {
                ui.is_paused = true;
            }
        }
        ImGui::SameLine();

        if (ImGui::Button(" Step ", ImVec2(70.0f, 26.0f))) {
            ui.single_step_requested = true;
            ui.is_paused = true;
        }
        ImGui::SameLine();

        if (ImGui::Button(" Reset ", ImVec2(70.0f, 26.0f))) {
            ui.reset_requested = true;
        }

        float ts = (float)ui.time_scale;
        if (ImGui::SliderFloat("Time Scale", &ts, 0.1f, 5.0f, "%.1fx")) {
            ui.time_scale = (double)ts;
        }
    }

    ImGui::Separator();

    // 4. Visual Rendering Options
    if (ImGui::CollapsingHeader("Visual & Display Options", ImGuiTreeNodeFlags_DefaultOpen)) {
        float thick_ex = (float)render_settings.thickness_exaggeration;
        if (ImGui::SliderFloat("Coin Visual Thickness", &thick_ex, 1.0f, 5.0f, "%.1fx")) {
            render_settings.thickness_exaggeration = (double)thick_ex;
        }

        ImGui::Checkbox("Follow Camera", &render_settings.follow_camera);
        ImGui::SameLine();
        ImGui::Checkbox("Show Trail", &render_settings.show_trail);

        ImGui::Checkbox("Stroboscopic Ghosts", &render_settings.show_ghosts);
        ImGui::SameLine();
        ImGui::Checkbox("Show Force Vectors", &render_settings.show_forces);

        if (ImGui::Checkbox("Compare Previous Runs", &plot_data.compare_previous)) {
            // Toggled
        }
        if (plot_data.compare_previous && ImGui::Button("Clear Previous Runs")) {
            plot_data.previous_runs.clear();
        }
    }

    ImGui::Separator();

    // 5. Physical Parameters (Fluid, Coefficients, Tank)
    if (ImGui::CollapsingHeader("Physical Parameters & Coefficients")) {
        // Fluid temperature presets
        ImGui::Text("Water Temperature Preset:");
        ImGui::SameLine();
        if (ImGui::Button("10°C")) {
            fluid.rho_f = 999.7;
            fluid.mu = 0.001307;
        }
        ImGui::SameLine();
        if (ImGui::Button("20°C")) {
            fluid.rho_f = 998.2;
            fluid.mu = 0.001002;
        }
        ImGui::SameLine();
        if (ImGui::Button("30°C")) {
            fluid.rho_f = 995.7;
            fluid.mu = 0.000798;
        }

        float rf = (float)fluid.rho_f;
        if (ImGui::DragFloat("Fluid Density rho_f [kg/m^3]", &rf, 1.0f, 500.0f, 2000.0f, "%.1f")) fluid.rho_f = rf;

        float mu_val = (float)fluid.mu;
        if (ImGui::DragFloat("Viscosity mu [Pa*s]", &mu_val, 1e-5f, 1e-4f, 0.05f, "%.5f")) fluid.mu = mu_val;

        // Andersen Coefficients
        bool non_default = (coeffs.C_T != default_coeffs.C_T ||
                            coeffs.C_R != default_coeffs.C_R ||
                            coeffs.C_D0 != default_coeffs.C_D0 ||
                            coeffs.C_D1 != default_coeffs.C_D1 ||
                            coeffs.C_tau != default_coeffs.C_tau ||
                            coeffs.c_lin != default_coeffs.c_lin ||
                            coeffs.mu_1 != default_coeffs.mu_1);

        if (non_default) {
            ImGui::TextColored(ImVec4(0.85f, 0.35f, 0.1f, 1.0f), "[!] Non-default coefficients in use");
            if (ImGui::Button("Reset to Defaults")) {
                coeffs = default_coeffs;
            }
        }

        float ct = (float)coeffs.C_T;
        if (ImGui::DragFloat("C_T (Translational lift)", &ct, 0.02f, 0.0f, 3.0f, "%.2f")) coeffs.C_T = ct;
        float cr = (float)coeffs.C_R;
        if (ImGui::DragFloat("C_R (Rotational lift)", &cr, 0.05f, 0.0f, 10.0f, "%.3f")) coeffs.C_R = cr;
        float cd0 = (float)coeffs.C_D0;
        if (ImGui::DragFloat("C_D0 (Drag base)", &cd0, 0.02f, 0.0f, 3.0f, "%.2f")) coeffs.C_D0 = cd0;
        float cd1 = (float)coeffs.C_D1;
        if (ImGui::DragFloat("C_D1 (Drag angle dep)", &cd1, 0.02f, 0.0f, 3.0f, "%.2f")) coeffs.C_D1 = cd1;
        float ctau = (float)coeffs.C_tau;
        if (ImGui::DragFloat("C_tau (Quadratic damping)", &ctau, 0.005f, 0.0f, 0.5f, "%.3f")) coeffs.C_tau = ctau;
        float mu1 = (float)coeffs.mu_1;
        if (ImGui::DragFloat("mu_1 (Linear damping)", &mu1, 0.005f, 0.0f, 0.5f, "%.3f")) coeffs.mu_1 = mu1;

        // Tank dimensions
        float tw = (float)(tank.width * 100.0);
        if (ImGui::DragFloat("Tank Width [cm]", &tw, 1.0f, 10.0f, 200.0f, "%.1f cm")) tank.width = tw * 0.01;
        float th_w = (float)(tank.water_height * 100.0);
        if (ImGui::DragFloat("Water Height [cm]", &th_w, 1.0f, 10.0f, 200.0f, "%.1f cm")) tank.water_height = th_w * 0.01;
    }

    ImGui::Separator();

    // 6. Angle Sweep & Regime Study
    if (ImGui::CollapsingHeader("Angle Sweep & Regime Study")) {
        float sw_min = (float)ui.sweep_min_deg;
        float sw_max = (float)ui.sweep_max_deg;
        float sw_step = (float)ui.sweep_step_deg;

        ImGui::DragFloat("Min Angle [deg]", &sw_min, 1.0f, 0.0f, 360.0f, "%.0f°");
        ImGui::DragFloat("Max Angle [deg]", &sw_max, 1.0f, 0.0f, 360.0f, "%.0f°");
        ImGui::DragFloat("Step [deg]", &sw_step, 1.0f, 1.0f, 90.0f, "%.0f°");

        ui.sweep_min_deg = sw_min;
        ui.sweep_max_deg = sw_max;
        ui.sweep_step_deg = sw_step;

        if (ImGui::Button("Run Angle Sweep", ImVec2(160.0f, 26.0f))) {
            Model model(current_plate, fluid, coeffs);
            ui.sweep_results = run_angle_sweep(model, tank, classifier,
                                               ui.sweep_min_deg, ui.sweep_max_deg, ui.sweep_step_deg,
                                               ui.perturb_rad);
            ui.status_message = "Angle sweep completed: " + std::to_string(ui.sweep_results.size()) + " angles.";
        }

        if (!ui.sweep_results.empty()) {
            ImGui::SameLine();
            if (ImGui::Button("Export Sweep CSV")) {
                std::string fname = "sweep_" + current_plate.id + ".csv";
                if (export_sweep_csv(fname, ui.sweep_results)) {
                    ui.status_message = "Saved sweep to " + fname;
                } else {
                    ui.status_message = "Error writing " + fname;
                }
            }

            // Results table
            if (ImGui::BeginTable("SweepTable", 6, ImGuiTableFlags_Borders | ImGuiTableFlags_RowBg | ImGuiTableFlags_ScrollY, ImVec2(0.0f, 180.0f))) {
                ImGui::TableSetupColumn("Angle");
                ImGui::TableSetupColumn("Outcome");
                ImGui::TableSetupColumn("t [s]");
                ImGui::TableSetupColumn("Vy [cm/s]");
                ImGui::TableSetupColumn("Flips");
                ImGui::TableSetupColumn("Regime");
                ImGui::TableHeadersRow();

                for (const auto& row : ui.sweep_results) {
                    ImGui::TableNextRow();
                    ImGui::TableSetColumnIndex(0);
                    ImGui::Text("%.1f°", row.theta0_deg);

                    ImGui::TableSetColumnIndex(1);
                    if (row.outcome == Outcome::Bottom) ImGui::TextColored(ImVec4(0.1f, 0.6f, 0.2f, 1.0f), "Bottom");
                    else if (row.outcome == Outcome::Wall) ImGui::TextColored(ImVec4(0.8f, 0.2f, 0.2f, 1.0f), "Wall");
                    else ImGui::TextColored(ImVec4(0.7f, 0.5f, 0.1f, 1.0f), "Timeout");

                    ImGui::TableSetColumnIndex(2);
                    ImGui::Text("%.2f", row.t_fall);

                    ImGui::TableSetColumnIndex(3);
                    ImGui::Text("%.1f", row.mean_vy * 100.0);

                    ImGui::TableSetColumnIndex(4);
                    ImGui::Text("%d", row.n_flips);

                    ImGui::TableSetColumnIndex(5);
                    std::string r_str = regime_to_string(row.regime);
                    if (row.regime == Regime::Steady) ImGui::TextColored(ImVec4(0.1f, 0.6f, 0.2f, 1.0f), "%s", r_str.c_str());
                    else if (row.regime == Regime::Fluttering) ImGui::TextColored(ImVec4(0.1f, 0.4f, 0.8f, 1.0f), "%s", r_str.c_str());
                    else if (row.regime == Regime::Tumbling) ImGui::TextColored(ImVec4(0.85f, 0.45f, 0.1f, 1.0f), "%s", r_str.c_str());
                    else ImGui::TextColored(ImVec4(0.6f, 0.2f, 0.7f, 1.0f), "%s", r_str.c_str());
                }
                ImGui::EndTable();
            }
        }
    }

    ImGui::Separator();

    // 7. Export Current Run
    if (ImGui::Button("Export Trajectory CSV")) {
        ui.export_csv_requested = true;
    }
    ImGui::SameLine();
    if (ImGui::Button("Take Screenshot (PNG)")) {
        ui.screenshot_requested = true;
    }

    if (!ui.status_message.empty()) {
        ImGui::TextColored(ImVec4(0.15f, 0.50f, 0.80f, 1.0f), "%s", ui.status_message.c_str());
    }

    ImGui::End();
}

void UIController::render_status_bar(const PlateConfig& plate,
                                     const FluidConfig& fluid,
                                     double current_time,
                                     const State& current_state,
                                     Regime current_regime,
                                     Outcome current_outcome,
                                     float screen_width,
                                     float bar_height) {
    ImGui::SetNextWindowPos(ImVec2(0.0f, ImGui::GetIO().DisplaySize.y - bar_height));
    ImGui::SetNextWindowSize(ImVec2(screen_width, bar_height));

    ImGuiWindowFlags flags = ImGuiWindowFlags_NoDecoration |
                             ImGuiWindowFlags_NoInputs |
                             ImGuiWindowFlags_NoMove |
                             ImGuiWindowFlags_NoSavedSettings;

    ImGui::Begin("StatusBar", nullptr, flags);

    double I_star = plate.I_star(fluid.rho_f);
    double U_t = plate.U_t(fluid.rho_f, fluid.g);
    double Re = (fluid.mu > 0.0) ? (fluid.rho_f * U_t * plate.L / fluid.mu) : 0.0;

    ImGui::Text("Time: %.3f s | I*: %.3f | Re: %.0f | X: %+.1f cm | Y: %+.1f cm | theta: %+.1f°  ",
                current_time, I_star, Re, current_state[0] * 100.0, current_state[1] * 100.0,
                current_state[2] * (180.0 / M_PI));

    ImGui::SameLine();
    ImGui::Text("| Regime: ");
    ImGui::SameLine();

    std::string r_str = regime_to_string(current_regime);
    if (current_regime == Regime::Steady) {
        ImGui::TextColored(ImVec4(0.1f, 0.65f, 0.25f, 1.0f), "[ Steady Descent ]");
    } else if (current_regime == Regime::Fluttering) {
        ImGui::TextColored(ImVec4(0.15f, 0.45f, 0.85f, 1.0f), "[ Fluttering ]");
    } else if (current_regime == Regime::Tumbling) {
        ImGui::TextColored(ImVec4(0.85f, 0.45f, 0.10f, 1.0f), "[ Tumbling ]");
    } else {
        ImGui::TextColored(ImVec4(0.65f, 0.25f, 0.75f, 1.0f), "[ Chaotic / Mixed ]");
    }

    ImGui::SameLine();
    ImGui::Text("  Outcome: ");
    ImGui::SameLine();

    if (current_outcome == Outcome::Running) {
        ImGui::TextColored(ImVec4(0.35f, 0.40f, 0.45f, 1.0f), "Running");
    } else if (current_outcome == Outcome::Bottom) {
        ImGui::TextColored(ImVec4(0.10f, 0.65f, 0.20f, 1.0f), "Landed (Bottom)");
    } else if (current_outcome == Outcome::Wall) {
        ImGui::TextColored(ImVec4(0.85f, 0.20f, 0.20f, 1.0f), "Hit Wall");
    } else {
        ImGui::TextColored(ImVec4(0.75f, 0.50f, 0.10f, 1.0f), "Timeout");
    }

    ImGui::End();
}

} // namespace autumn
