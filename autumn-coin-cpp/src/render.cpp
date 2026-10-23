#include "render.hpp"
#include "raylib.h"
#include <cmath>
#include <algorithm>
#include <string>

namespace autumn {

static void draw_arrow(Vector2 start, Vector2 dir, float length, Color col, const char* label) {
    if (length < 3.0f) return;
    float angle = std::atan2(dir.y, dir.x);
    Vector2 end = { start.x + dir.x * length, start.y + dir.y * length };
    DrawLineEx(start, end, 2.0f, col);
    float arrow_sz = 6.0f;
    Vector2 p1 = { end.x - arrow_sz * std::cos(angle - 0.45f), end.y - arrow_sz * std::sin(angle - 0.45f) };
    Vector2 p2 = { end.x - arrow_sz * std::cos(angle + 0.45f), end.y - arrow_sz * std::sin(angle + 0.45f) };
    DrawTriangle(end, p1, p2, col);
    DrawTriangle(end, p2, p1, col);
    if (label && label[0] != '\0') {
        DrawText(label, (int)(end.x + 5), (int)(end.y - 6), 11, col);
    }
}

Vec2 TankRenderer::world_to_screen(double wx, double wy, const TankConfig& tank, const RenderSettings& settings) const {
    Vec2 s;
    s.x = settings.tank_origin_px.x + (wx + tank.width * 0.5) * settings.px_per_m;
    s.y = settings.tank_origin_px.y + (-wy) * settings.px_per_m;
    return s;
}

void TankRenderer::draw(const TankConfig& tank,
                        const Model& model,
                        const State& current_state,
                        const std::vector<Sample>& trail_samples,
                        const std::vector<std::vector<Vec2>>& ghost_trajectories,
                        const RenderSettings& settings,
                        int viewport_w,
                        int viewport_h) {
    RenderSettings eff = settings;

    // Follow camera mode: center vertically on current coin Y position
    if (settings.follow_camera) {
        double target_y = (viewport_h * 0.45) - (-current_state[1]) * settings.px_per_m;
        eff.tank_origin_px.y = target_y;
    }

    const Vec2 origin = eff.tank_origin_px;
    const double W_px = tank.width * eff.px_per_m;
    const double H_px = tank.water_height * eff.px_per_m;
    const double glass_px = std::max(8.0, tank.glass_thickness * eff.px_per_m * 1.5);

    // 1. Water Fill inside tank (Vibrant aquatic gradient)
    DrawRectangleGradientV((int)origin.x, (int)origin.y, (int)W_px, (int)H_px,
                           Color{ 175, 222, 248, 210 },
                           Color{ 110, 180, 225, 240 });

    // Water surface line (y = 0) with crisp wave indicator
    DrawLineEx(Vector2{ (float)origin.x, (float)origin.y },
               Vector2{ (float)(origin.x + W_px), (float)origin.y },
               3.0f, Color{ 24, 125, 195, 255 });

    // Surface label
    DrawText("Water Surface (Y = 0)", (int)(origin.x + 10), (int)(origin.y - 18), 11, Color{ 20, 90, 150, 240 });

    // Tank title at top
    DrawText("GLASS WATER CONTAINER (38 x 38 cm)", (int)(origin.x + W_px * 0.5 - 120), (int)(origin.y - 36), 13, Color{ 25, 50, 80, 255 });

    // 2. Centimetre ruler and scale on left glass
    const int total_cm = (int)std::round(tank.water_height * 100.0);
    for (int cm = 0; cm <= total_cm; cm += 1) {
        double wy = -(cm * 0.01);
        Vec2 tick_pos = world_to_screen(-tank.width * 0.5, wy, tank, eff);
        bool major = (cm % 5 == 0);
        float tick_len = major ? 12.0f : 5.0f;
        Color tick_col = major ? Color{ 25, 45, 70, 230 } : Color{ 90, 125, 155, 180 };

        DrawLineEx(Vector2{ (float)(tick_pos.x - tick_len), (float)tick_pos.y },
                   Vector2{ (float)tick_pos.x, (float)tick_pos.y },
                   major ? 2.0f : 1.0f, tick_col);

        if (major && cm % 5 == 0 && cm > 0) {
            std::string label = std::to_string(cm);
            DrawText(label.c_str(), (int)(tick_pos.x - tick_len - 20), (int)(tick_pos.y - 6), 11, Color{ 25, 45, 70, 240 });
        }
    }
    // Ruler units at top
    DrawText("cm", (int)(origin.x - 24), (int)(origin.y - 18), 11, Color{ 25, 45, 70, 240 });

    // 3. Ghost trajectories (from angle sweep)
    for (const auto& traj : ghost_trajectories) {
        if (traj.size() < 2) continue;
        for (size_t i = 1; i < traj.size(); ++i) {
            Vec2 p1 = world_to_screen(traj[i - 1].x, traj[i - 1].y, tank, eff);
            Vec2 p2 = world_to_screen(traj[i].x, traj[i].y, tank, eff);
            DrawLineEx(Vector2{ (float)p1.x, (float)p1.y },
                       Vector2{ (float)p2.x, (float)p2.y },
                       1.2f, Color{ 170, 185, 205, 120 });
        }
    }

    // 4. Stroboscopic ghost coins along trail
    if (eff.show_ghosts && !trail_samples.empty()) {
        const double step_s = eff.ghost_interval_ms * 1e-3;
        double next_t = step_s;
        for (const auto& samp : trail_samples) {
            if (samp.t >= next_t) {
                State s_ghost = { samp.X, samp.Y, samp.theta, samp.u, samp.v, samp.omega };
                auto g_corners = get_coin_corners(s_ghost, model.plate().L, model.plate().h, eff.thickness_exaggeration);
                Vec2 sc0 = world_to_screen(g_corners[0].x, g_corners[0].y, tank, eff);
                Vec2 sc1 = world_to_screen(g_corners[1].x, g_corners[1].y, tank, eff);
                Vec2 sc2 = world_to_screen(g_corners[2].x, g_corners[2].y, tank, eff);
                Vec2 sc3 = world_to_screen(g_corners[3].x, g_corners[3].y, tank, eff);

                Color gc = Color{ 100, 130, 170, 45 };
                Color g_line = Color{ 80, 110, 150, 80 };

                DrawTriangle(Vector2{ (float)sc0.x, (float)sc0.y }, Vector2{ (float)sc1.x, (float)sc1.y }, Vector2{ (float)sc2.x, (float)sc2.y }, gc);
                DrawTriangle(Vector2{ (float)sc0.x, (float)sc0.y }, Vector2{ (float)sc2.x, (float)sc2.y }, Vector2{ (float)sc1.x, (float)sc1.y }, gc);
                DrawTriangle(Vector2{ (float)sc0.x, (float)sc0.y }, Vector2{ (float)sc2.x, (float)sc2.y }, Vector2{ (float)sc3.x, (float)sc3.y }, gc);
                DrawTriangle(Vector2{ (float)sc0.x, (float)sc0.y }, Vector2{ (float)sc3.x, (float)sc3.y }, Vector2{ (float)sc2.x, (float)sc2.y }, gc);

                DrawLineEx(Vector2{ (float)sc0.x, (float)sc0.y }, Vector2{ (float)sc1.x, (float)sc1.y }, 1.0f, g_line);
                DrawLineEx(Vector2{ (float)sc1.x, (float)sc1.y }, Vector2{ (float)sc2.x, (float)sc2.y }, 1.0f, g_line);
                DrawLineEx(Vector2{ (float)sc2.x, (float)sc2.y }, Vector2{ (float)sc3.x, (float)sc3.y }, 1.0f, g_line);
                DrawLineEx(Vector2{ (float)sc3.x, (float)sc3.y }, Vector2{ (float)sc0.x, (float)sc0.y }, 1.0f, g_line);

                next_t += step_s;
            }
        }
    }

    // 5. Fading trail polyline
    if (eff.show_trail && trail_samples.size() >= 2) {
        size_t n = trail_samples.size();
        size_t start_idx = (n > (size_t)eff.max_trail_points) ? (n - (size_t)eff.max_trail_points) : 0;
        for (size_t i = start_idx + 1; i < n; ++i) {
            Vec2 p1 = world_to_screen(trail_samples[i - 1].X, trail_samples[i - 1].Y, tank, eff);
            Vec2 p2 = world_to_screen(trail_samples[i].X, trail_samples[i].Y, tank, eff);

            float frac = (float)(i - start_idx) / (float)(n - start_idx);
            unsigned char alpha = (unsigned char)(40 + 200 * frac);
            DrawLineEx(Vector2{ (float)p1.x, (float)p1.y },
                       Vector2{ (float)p2.x, (float)p2.y },
                       2.0f, Color{ 25, 75, 150, alpha });
        }
    }

    // 6. Draw Falling Coin (Rotated Rectangle)
    auto corners = get_coin_corners(current_state, model.plate().L, model.plate().h, eff.thickness_exaggeration);
    Vec2 c0 = world_to_screen(corners[0].x, corners[0].y, tank, eff);
    Vec2 c1 = world_to_screen(corners[1].x, corners[1].y, tank, eff);
    Vec2 c2 = world_to_screen(corners[2].x, corners[2].y, tank, eff);
    Vec2 c3 = world_to_screen(corners[3].x, corners[3].y, tank, eff);

    Vector2 v0 = { (float)c0.x, (float)c0.y };
    Vector2 v1 = { (float)c1.x, (float)c1.y };
    Vector2 v2 = { (float)c2.x, (float)c2.y };
    Vector2 v3 = { (float)c3.x, (float)c3.y };

    Color coin_body = (model.plate().material == "cupronickel") ? Color{ 195, 205, 215, 255 } : Color{ 228, 175, 45, 255 };
    Color coin_outline = Color{ 35, 35, 35, 255 };
    Color orientation_mark = Color{ 180, 30, 20, 255 };

    // Fill both triangles (dual winding for safety)
    DrawTriangle(v0, v1, v2, coin_body);
    DrawTriangle(v0, v2, v1, coin_body);
    DrawTriangle(v0, v2, v3, coin_body);
    DrawTriangle(v0, v3, v2, coin_body);

    // Outline
    DrawLineEx(v0, v1, 2.0f, coin_outline);
    DrawLineEx(v1, v2, 2.0f, coin_outline);
    DrawLineEx(v2, v3, 2.0f, coin_outline);
    DrawLineEx(v3, v0, 2.0f, coin_outline);

    // Orientation stripe on top chord edge (v2 -> v3) to show spin/tumble direction
    if (eff.show_orientation_stripe) {
        DrawLineEx(v2, v3, 3.5f, orientation_mark);
    }

    // Center of mass dot
    Vec2 cm_s = world_to_screen(current_state[0], current_state[1], tank, eff);
    if (eff.show_center_dot) {
        DrawCircleV(Vector2{ (float)cm_s.x, (float)cm_s.y }, 2.5f, Color{ 30, 30, 30, 255 });
    }

    // 7. Live Force & Velocity Vectors (if enabled)
    if (eff.show_forces) {
        Vector2 cm_v = { (float)cm_s.x, (float)cm_s.y };

        // Velocity vector in lab frame:
        double c_th = std::cos(current_state[2]);
        double s_th = std::sin(current_state[2]);
        double vx = current_state[3] * c_th - current_state[4] * s_th;
        double vy = current_state[3] * s_th + current_state[4] * c_th;
        double speed = std::hypot(vx, vy);

        if (speed > 1e-4) {
            Vector2 v_dir = { (float)(vx / speed), (float)(-vy / speed) }; // screen Y is down
            float v_len = (float)std::min(70.0, speed * 120.0);
            draw_arrow(cm_v, v_dir, v_len, Color{ 30, 160, 50, 255 }, "V");
        }

        double FLx = 0.0, FLy = 0.0, FDx = 0.0, FDy = 0.0;
        model.lab_forces(current_state, FLx, FLy, FDx, FDy);

        double lift_mag = std::hypot(FLx, FLy);
        if (lift_mag > 1e-5) {
            Vector2 l_dir = { (float)(FLx / lift_mag), (float)(-FLy / lift_mag) };
            float l_len = (float)std::min(60.0, lift_mag * 400.0);
            draw_arrow(cm_v, l_dir, l_len, Color{ 220, 40, 40, 255 }, "L");
        }

        double drag_mag = std::hypot(FDx, FDy);
        if (drag_mag > 1e-5) {
            Vector2 d_dir = { (float)(FDx / drag_mag), (float)(-FDy / drag_mag) };
            float d_len = (float)std::min(60.0, drag_mag * 400.0);
            draw_arrow(cm_v, d_dir, d_len, Color{ 140, 40, 190, 255 }, "D");
        }

        // Net buoyant weight (points downward in lab -> down in screen)
        double W_net = (model.mass() - model.mass_fluid()) * model.fluid().g;
        if (W_net > 1e-5) {
            Vector2 w_dir = { 0.0f, 1.0f }; // down in screen
            float w_len = (float)std::min(50.0, W_net * 400.0);
            draw_arrow(cm_v, w_dir, w_len, Color{ 20, 100, 210, 255 }, "W_b");
        }
    }

    // 8. Glass walls and floor (rendered with alpha in front)
    Color glass_tint = Color{ 190, 225, 238, 160 };
    Color glass_border = Color{ 70, 130, 165, 255 };
    Color glass_highlight = Color{ 255, 255, 255, 220 };

    // Left glass wall
    Rectangle left_wall = { (float)(origin.x - glass_px), (float)(origin.y - 12.0),
                            (float)glass_px, (float)(H_px + glass_px + 12.0) };
    DrawRectangleRec(left_wall, glass_tint);
    DrawRectangleLinesEx(left_wall, 2.0f, glass_border);
    DrawLineEx(Vector2{ (float)(origin.x - glass_px + 2.0), (float)(origin.y - 10.0) },
               Vector2{ (float)(origin.x - glass_px + 2.0), (float)(origin.y + H_px + glass_px) },
               2.0f, glass_highlight);

    // Right glass wall
    Rectangle right_wall = { (float)(origin.x + W_px), (float)(origin.y - 12.0),
                             (float)glass_px, (float)(H_px + glass_px + 12.0) };
    DrawRectangleRec(right_wall, glass_tint);
    DrawRectangleLinesEx(right_wall, 2.0f, glass_border);

    // Bottom floor
    Rectangle floor_rect = { (float)(origin.x - glass_px), (float)(origin.y + H_px),
                             (float)(W_px + 2.0 * glass_px), (float)glass_px };
    DrawRectangleRec(floor_rect, glass_tint);
    DrawRectangleLinesEx(floor_rect, 2.0f, glass_border);

    // Inner tank boundary line
    DrawRectangleLinesEx(Rectangle{ (float)origin.x, (float)origin.y, (float)W_px, (float)H_px }, 1.5f, Color{ 70, 130, 165, 200 });
}

} // namespace autumn
