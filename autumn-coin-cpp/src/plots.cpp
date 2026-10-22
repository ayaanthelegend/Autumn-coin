#include "plots.hpp"
#include "imgui.h"
#include "implot.h"
#include <cmath>
#include <algorithm>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace autumn {

void PlotData::add_sample(const Sample& s) {
    float t = (float)s.t;
    float x_cm = (float)(s.X * 100.0);
    float y_cm = (float)(s.Y * 100.0);
    float th_deg = (float)(s.theta * (180.0 / M_PI));
    float om = (float)s.omega;
    float vy_cm = (float)(-s.vy * 100.0); // positive downward fall speed
    double c = std::cos(s.theta);
    double sn = std::sin(s.theta);
    float vx_cm = (float)((s.u * c - s.v * sn) * 100.0);
    float depth_cm = (float)(-s.Y * 100.0);
    double th_wrap = std::fmod(std::fmod(s.theta, 2.0 * M_PI) + 2.0 * M_PI, 2.0 * M_PI);
    float th_mod = (float)th_wrap;
    float al_deg = (float)(s.alpha * (180.0 / M_PI));

    traj_xy.add(x_cm, y_cm);
    theta.add(t, th_deg);
    omega.add(t, om);
    speed_y.add(t, vy_cm);
    speed_x.add(t, vx_cm);
    depth.add(t, depth_cm);
    phase.add(th_mod, om);
    alpha.add(t, al_deg);
}

void PlotData::archive_run(const std::vector<Sample>& samples) {
    if (samples.empty()) return;
    std::vector<Vec2> traj;
    traj.reserve(samples.size());
    for (const auto& s : samples) {
        traj.push_back({ s.X * 100.0, s.Y * 100.0 });
    }
    previous_runs.push_back(std::move(traj));
    if (previous_runs.size() > 12) {
        previous_runs.erase(previous_runs.begin());
    }
}

LivePlotPanel::LivePlotPanel() {}

void LivePlotPanel::setup_light_style() {
    ImPlot::StyleColorsLight();
    ImPlotStyle& style = ImPlot::GetStyle();
    style.Colors[ImPlotCol_PlotBg] = ImVec4(1.0f, 1.0f, 1.0f, 1.0f);
    style.Colors[ImPlotCol_FrameBg] = ImVec4(0.97f, 0.98f, 0.99f, 1.0f);
    style.Colors[ImPlotCol_PlotBorder] = ImVec4(0.70f, 0.75f, 0.80f, 1.0f);
    style.Colors[ImPlotCol_LegendBg] = ImVec4(1.0f, 1.0f, 1.0f, 0.90f);
    style.Colors[ImPlotCol_LegendBorder] = ImVec4(0.75f, 0.80f, 0.85f, 1.0f);
    style.Colors[ImPlotCol_LegendText] = ImVec4(0.08f, 0.10f, 0.12f, 1.0f);
    style.Colors[ImPlotCol_AxisText] = ImVec4(0.08f, 0.10f, 0.12f, 1.0f);
    style.Colors[ImPlotCol_AxisGrid] = ImVec4(0.88f, 0.90f, 0.92f, 1.0f);
    style.Colors[ImPlotCol_Line] = ImVec4(0.12f, 0.40f, 0.75f, 1.0f);
}

static void plot_scroll_buf(const char* label, const ScrollBuf& buf, ImVec4 color = ImVec4(0.15f, 0.45f, 0.80f, 1.0f)) {
    if (buf.empty()) return;
    ImPlot::SetNextLineStyle(color, 2.0f);
    if (buf.size() < buf.max) {
        ImPlot::PlotLine(label, buf.x.data(), buf.y.data(), buf.size());
    } else {
        ImPlot::PlotLine(label, buf.x.data(), buf.y.data(), buf.size(), 0, buf.off);
    }
}

void LivePlotPanel::render(PlotData& data, float width, float height) {
    if (!style_initialized_) {
        setup_light_style();
        style_initialized_ = true;
    }

    ImGui::BeginChild("LivePlotsRegion", ImVec2(width, height), true);

    if (ImGui::BeginTabBar("PlotTabs")) {
        // Tab 1: Trajectory (1:1 equal aspect ratio)
        if (ImGui::BeginTabItem("Trajectory (X-Y)")) {
            ImVec2 avail = ImGui::GetContentRegionAvail();
            if (ImPlot::BeginPlot("##TrajectoryPlot", avail, ImPlotFlags_Equal)) {
                ImPlot::SetupAxes("X [cm]", "Y [cm]");
                ImPlot::SetupLegend(ImPlotLocation_NorthEast);

                // Overlay previous runs if enabled
                if (data.compare_previous) {
                    int prev_idx = 0;
                    for (const auto& run : data.previous_runs) {
                        if (run.size() >= 2) {
                            std::vector<float> px(run.size()), py(run.size());
                            for (size_t i = 0; i < run.size(); ++i) {
                                px[i] = (float)run[i].x;
                                py[i] = (float)run[i].y;
                            }
                            std::string lbl = "Prev Run " + std::to_string(++prev_idx);
                            ImPlot::SetNextLineStyle(ImVec4(0.65f, 0.70f, 0.75f, 0.6f), 1.0f);
                            ImPlot::PlotLine(lbl.c_str(), px.data(), py.data(), (int)px.size());
                        }
                    }
                }

                plot_scroll_buf("Trajectory", data.traj_xy, ImVec4(0.10f, 0.40f, 0.80f, 1.0f));
                ImPlot::EndPlot();
            }
            ImGui::EndTabItem();
        }

        // Tab 2: Orientation theta(t) & omega(t)
        if (ImGui::BeginTabItem("Angle & Rotation")) {
            ImVec2 avail = ImGui::GetContentRegionAvail();
            float half_h = (avail.y - 10.0f) * 0.5f;

            if (ImPlot::BeginPlot("##AnglePlot", ImVec2(avail.x, half_h))) {
                ImPlot::SetupAxes("Time t [s]", "Angle theta [deg]");
                plot_scroll_buf("theta(t)", data.theta, ImVec4(0.85f, 0.25f, 0.20f, 1.0f));
                ImPlot::EndPlot();
            }

            if (ImPlot::BeginPlot("##OmegaPlot", ImVec2(avail.x, half_h))) {
                ImPlot::SetupAxes("Time t [s]", "Angular Velocity omega [rad/s]");
                plot_scroll_buf("omega(t)", data.omega, ImVec4(0.20f, 0.60f, 0.30f, 1.0f));
                ImPlot::EndPlot();
            }
            ImGui::EndTabItem();
        }

        // Tab 3: Velocities & Depth
        if (ImGui::BeginTabItem("Speed & Depth")) {
            ImVec2 avail = ImGui::GetContentRegionAvail();
            float half_h = (avail.y - 10.0f) * 0.5f;

            if (ImPlot::BeginPlot("##VelocitiesPlot", ImVec2(avail.x, half_h))) {
                ImPlot::SetupAxes("Time t [s]", "Speed [cm/s]");
                plot_scroll_buf("Vertical -vy [cm/s]", data.speed_y, ImVec4(0.10f, 0.45f, 0.85f, 1.0f));
                plot_scroll_buf("Horizontal vx [cm/s]", data.speed_x, ImVec4(0.80f, 0.45f, 0.10f, 1.0f));
                ImPlot::EndPlot();
            }

            if (ImPlot::BeginPlot("##DepthPlot", ImVec2(avail.x, half_h))) {
                ImPlot::SetupAxes("Time t [s]", "Depth [cm]");
                plot_scroll_buf("Depth [cm]", data.depth, ImVec4(0.35f, 0.20f, 0.65f, 1.0f));
                ImPlot::EndPlot();
            }
            ImGui::EndTabItem();
        }

        // Tab 4: Phase Portrait & Angle of Attack
        if (ImGui::BeginTabItem("Phase Portrait")) {
            ImVec2 avail = ImGui::GetContentRegionAvail();
            float half_h = (avail.y - 10.0f) * 0.5f;

            if (ImPlot::BeginPlot("##PhasePlot", ImVec2(avail.x, half_h))) {
                ImPlot::SetupAxes("theta mod 2pi [rad]", "omega [rad/s]");
                plot_scroll_buf("Phase (theta vs omega)", data.phase, ImVec4(0.80f, 0.15f, 0.55f, 1.0f));
                ImPlot::EndPlot();
            }

            if (ImPlot::BeginPlot("##AlphaPlot", ImVec2(avail.x, half_h))) {
                ImPlot::SetupAxes("Time t [s]", "Angle of Attack alpha [deg]");
                plot_scroll_buf("alpha [deg]", data.alpha, ImVec4(0.15f, 0.65f, 0.65f, 1.0f));
                ImPlot::EndPlot();
            }
            ImGui::EndTabItem();
        }

        ImGui::EndTabBar();
    }

    ImGui::EndChild();
}

} // namespace autumn
