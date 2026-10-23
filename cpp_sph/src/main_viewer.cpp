#include <cmath>
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <windowsx.h>

#include "software_renderer.hpp"
#include "sph_solver.hpp"
#include "ode_replay.hpp"
#include "config.hpp"

#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <deque>
#include <algorithm>
#include <chrono>

namespace sph {

// 6-state Quasi-steady Andersen ODE Simulator in C++
struct ODESimulator {
    double X = 0.0;
    double Y = 0.0;
    double theta = 0.087266; // 5 deg
    double u = 0.0;
    double v = 0.0;
    double omega = 0.0;

    double L = 0.024;
    double h = 0.0018;
    double rho_f = 998.0;
    double rho_s = 2700.0;
    double g = 9.81;

    double C_D0 = 1.4;
    double C_D1 = 1.0;
    double C_T = 1.2;
    double C_R = 1.6;
    double C_tau = 0.075;
    double mu_1 = 0.2;
    double c_lin = 0.0;

    double sim_time = 0.0;
    bool is_done = false;

    // Derived
    double a() const { return L * 0.5; }
    double b() const { return h * 0.5; }
    double mass() const { return rho_s * M_PI * a() * b(); }
    double mass_fluid() const { return rho_f * M_PI * a() * b(); }
    double I_solid() const { return 0.25 * mass() * (a() * a() + b() * b()); }

    double m11() const { return rho_f * M_PI * b() * b(); }
    double m22() const { return rho_f * M_PI * a() * a(); }
    double I_a() const { double diff = a() * a() - b() * b(); return (1.0 / 8.0) * rho_f * M_PI * diff * diff; }

    double M_u() const { return mass() + m11(); }
    double M_v() const { return mass() + m22(); }
    double I_tot() const { return I_solid() + I_a(); }
    double I_star() const { return I_solid() / (0.25 * rho_f * M_PI * (a() * a() + b() * b()) * (a() * a() + b() * b())); }

    void reset(double new_I_star, double new_theta_rad = 0.087266) {
        // adjust rho_s to match target I_star
        double a_val = a(), b_val = b();
        double geom_factor = (a_val * a_val + b_val * b_val);
        double denom = 0.25 * rho_f * M_PI * geom_factor * geom_factor;
        // I_solid = 0.25 * (rho_s * pi * a * b) * geom_factor
        // I_star = rho_s * a * b / (rho_f * geom_factor)
        rho_s = new_I_star * rho_f * geom_factor / (a_val * b_val);

        X = 0.0;
        Y = 0.0;
        theta = new_theta_rad;
        u = 0.0;
        v = 0.0;
        omega = 0.0;
        sim_time = 0.0;
        is_done = false;
    }

    void derivatives(double s_X, double s_Y, double s_th, double s_u, double s_v, double s_om,
                     double& dX, double& dY, double& dth, double& du, double& dv, double& dom,
                     double& out_F_L_x, double& out_F_L_y, double& out_F_D_x, double& out_F_D_y) const {
        double cos_th = std::cos(s_th);
        double sin_th = std::sin(s_th);

        dX = s_u * cos_th - s_v * sin_th;
        dY = s_u * sin_th + s_v * cos_th;
        dth = s_om;

        double speed = std::hypot(s_u, s_v);
        double eps_V = 1e-6;
        double trans_term = (speed < eps_V) ? 0.0 : -C_T * L * (s_u * s_v / speed);
        double rot_term = 0.5 * C_R * (L * L) * s_om;
        double gamma = trans_term + rot_term;

        double alpha = std::atan2(-s_v, s_u);
        double c_d = C_D0 - C_D1 * std::cos(2.0 * alpha);

        double f_u = 0.5 * rho_f * L * c_d * speed * s_u;
        double f_v = 0.5 * rho_f * L * c_d * speed * s_v;

        double u_char = std::sqrt(std::max(rho_s / rho_f - 1.0, 0.0) * g * (h * 0.5));
        double c_lin_phys = (M_PI / 8.0) * rho_f * (L * L * L) * u_char * mu_1;
        double c_lin_eff = c_lin + c_lin_phys;
        double tau = 0.5 * C_tau * rho_f * std::pow(L, 4.0) * std::abs(s_om) * s_om + c_lin_eff * s_om;

        double buoyant_weight = (mass() - mass_fluid()) * g;
        double g_u = buoyant_weight * sin_th;
        double g_v = buoyant_weight * cos_th;

        double lift_u = rho_f * gamma * s_v;
        double lift_v = rho_f * gamma * s_u;

        du = (M_v() * s_v * s_om - lift_u - f_u - g_u) / M_u();
        dv = (-M_u() * s_u * s_om + lift_v - f_v - g_v) / M_v();
        dom = ((m11() - m22()) * s_u * s_v - tau) / I_tot();

        // Lab forces for visualization
        out_F_L_x = -rho_f * gamma * dY;
        out_F_L_y =  rho_f * gamma * dX;
        out_F_D_x = -0.5 * rho_f * L * c_d * speed * dX;
        out_F_D_y = -0.5 * rho_f * L * c_d * speed * dY;
    }

    void step(double dt, double& out_FLx, double& out_FLy, double& out_FDx, double& out_FDy) {
        // 4th order Runge-Kutta
        double k1_X, k1_Y, k1_th, k1_u, k1_v, k1_om, fl1x, fl1y, fd1x, fd1y;
        derivatives(X, Y, theta, u, v, omega, k1_X, k1_Y, k1_th, k1_u, k1_v, k1_om, fl1x, fl1y, fd1x, fd1y);

        double k2_X, k2_Y, k2_th, k2_u, k2_v, k2_om, fl2x, fl2y, fd2x, fd2y;
        derivatives(X + 0.5 * dt * k1_X, Y + 0.5 * dt * k1_Y, theta + 0.5 * dt * k1_th,
                    u + 0.5 * dt * k1_u, v + 0.5 * dt * k1_v, omega + 0.5 * dt * k1_om,
                    k2_X, k2_Y, k2_th, k2_u, k2_v, k2_om, fl2x, fl2y, fd2x, fd2y);

        double k3_X, k3_Y, k3_th, k3_u, k3_v, k3_om, fl3x, fl3y, fd3x, fd3y;
        derivatives(X + 0.5 * dt * k2_X, Y + 0.5 * dt * k2_Y, theta + 0.5 * dt * k2_th,
                    u + 0.5 * dt * k2_u, v + 0.5 * dt * k2_v, omega + 0.5 * dt * k2_om,
                    k3_X, k3_Y, k3_th, k3_u, k3_v, k3_om, fl3x, fl3y, fd3x, fd3y);

        double k4_X, k4_Y, k4_th, k4_u, k4_v, k4_om, fl4x, fl4y, fd4x, fd4y;
        derivatives(X + dt * k3_X, Y + dt * k3_Y, theta + dt * k3_th,
                    u + dt * k3_u, v + dt * k3_v, omega + dt * k3_om,
                    k4_X, k4_Y, k4_th, k4_u, k4_v, k4_om, fl4x, fl4y, fd4x, fd4y);

        X += (dt / 6.0) * (k1_X + 2.0 * k2_X + 2.0 * k3_X + k4_X);
        Y += (dt / 6.0) * (k1_Y + 2.0 * k2_Y + 2.0 * k3_Y + k4_Y);
        theta += (dt / 6.0) * (k1_th + 2.0 * k2_th + 2.0 * k3_th + k4_th);
        u += (dt / 6.0) * (k1_u + 2.0 * k2_u + 2.0 * k3_u + k4_u);
        v += (dt / 6.0) * (k1_v + 2.0 * k2_v + 2.0 * k3_v + k4_v);
        omega += (dt / 6.0) * (k1_om + 2.0 * k2_om + 2.0 * k3_om + k4_om);

        sim_time += dt;

        out_FLx = fl1x;
        out_FLy = fl1y;
        out_FDx = fd1x;
        out_FDy = fd1y;
    }
};

struct SyntheticVortex {
    double x, y;
    double strength;
    double life = 2.5; // seconds
};

struct VisualizerState {
    int mode = 0; // 0 = Mode A (ODE), 1 = Mode B (SPH)
    bool paused = false;
    double playback_speed = 0.3; // Default 0.3x slow-motion
    bool show_vectors = true;
    bool ensemble_mode = false;
    int color_mode_sph = 0; // 0 = speed, 1 = vorticity, 2 = pressure

    double current_I_star = 0.68;
    double current_theta0_deg = 5.0;
    double current_mu = 0.001; // water

    ODESimulator ode;
    std::vector<ODESimulator> ensemble_coins;

    SPHSolver sph;
    bool sph_initialized = false;

    std::deque<std::pair<double, double>> path_trail; // (X, Y)
    std::deque<double> history_time;
    std::deque<double> history_theta;
    std::deque<double> history_speed;
    std::deque<double> history_vy;

    std::vector<SyntheticVortex> shed_vortices;
    double prev_omega = 0.0;

    double FLx = 0.0, FLy = 0.0, FDx = 0.0, FDy = 0.0;

    void init_ode() {
        ode.reset(current_I_star, current_theta0_deg * M_PI / 180.0);
        path_trail.clear();
        history_time.clear();
        history_theta.clear();
        history_speed.clear();
        history_vy.clear();
        shed_vortices.clear();
        prev_omega = 0.0;

        if (ensemble_mode) {
            ensemble_coins.clear();
            for (int k = -7; k <= 7; ++k) {
                ODESimulator sim = ode;
                double perturbed_th = (current_theta0_deg + k * 0.15) * M_PI / 180.0;
                sim.reset(current_I_star, perturbed_th);
                ensemble_coins.push_back(sim);
            }
        }
    }

    void init_sph() {
        FluidConfig f_cfg;
        f_cfg.rho0 = 998.0;
        f_cfg.mu = current_mu;
        f_cfg.gamma = 7.0;

        RigidPlateConfig r_cfg;
        r_cfg.L = 0.024;
        r_cfg.h = 0.0018;
        r_cfg.rho_s = current_I_star * 998.0 * ((0.012 * 0.012 + 0.0009 * 0.0009) / (0.012 * 0.0009));
        r_cfg.theta = current_theta0_deg * M_PI / 180.0;
        r_cfg.pos = {0.0, 0.40};

        SPHConfig s_cfg;
        s_cfg.dx = 0.0020;
        s_cfg.h_factor = 1.3;
        s_cfg.dt = 0.0001;
        s_cfg.alpha_art = 0.0;
        s_cfg.use_shepard_density = true;

        DomainConfig d_cfg;
        d_cfg.x_min = -0.15;
        d_cfg.x_max = 0.15;
        d_cfg.y_min = -0.50;
        d_cfg.y_max = 0.50;

        sph = SPHSolver(f_cfg, s_cfg, d_cfg);
        sph.add_rigid_ellipse(r_cfg);
        sph.add_fluid_block(-0.14, 0.14, -0.48, 0.48, s_cfg.dx);
        sph_initialized = true;
    }

    std::string get_regime_badge() const {
        if (current_I_star <= 0.08) return "STEADY";
        if (current_I_star <= 1.0) return "FLUTTERING";
        if (current_I_star <= 1.8) return "TUMBLING";
        return "MIXED / CHAOTIC";
    }
};

} // namespace sph

// Global visualizer state & renderer
static sph::VisualizerState g_state;
static sph::SoftwareRenderer g_renderer(1360, 800, 1800.0);

static void draw_arrow(sph::SoftwareRenderer& ren, int x0, int y0, double vx, double vy, double scale, sph::ColorRGBA col) {
    int x1 = x0 + static_cast<int>(std::round(vx * scale));
    int y1 = y0 - static_cast<int>(std::round(vy * scale)); // screen Y inverted
    ren.draw_line(x0, y0, x1, y1, col, 2);

    // Arrowhead
    double len = std::hypot(x1 - x0, y1 - y0);
    if (len > 4.0) {
        double ux = (x1 - x0) / len;
        double uy = (y1 - y0) / len;
        double perp_x = -uy;
        double perp_y = ux;
        int hx1 = x1 - static_cast<int>(std::round(ux * 6.0 - perp_x * 4.0));
        int hy1 = y1 - static_cast<int>(std::round(uy * 6.0 - perp_y * 4.0));
        int hx2 = x1 - static_cast<int>(std::round(ux * 6.0 + perp_x * 4.0));
        int hy2 = y1 - static_cast<int>(std::round(uy * 6.0 + perp_y * 4.0));
        ren.draw_line(x1, y1, hx1, hy1, col, 2);
        ren.draw_line(x1, y1, hx2, hy2, col, 2);
    }
}

static void render_visualizer_frame(sph::SoftwareRenderer& ren, sph::VisualizerState& st) {
    ren.clear({255, 255, 255, 255}); // Clean white background

    int sim_view_w = 940;
    int hud_view_x = 940;

    // Camera tracking coin position
    double cam_x = (st.mode == 0) ? st.ode.X : (st.sph.rigid_bodies.empty() ? 0.0 : st.sph.rigid_bodies[0].pos.x);
    double cam_y = (st.mode == 0) ? st.ode.Y : (st.sph.rigid_bodies.empty() ? 0.0 : st.sph.rigid_bodies[0].pos.y);
    ren.set_view(cam_x, cam_y, 1800.0);

    // 1. Draw Virtual Water Tank Boundaries
    int left_s, right_s, top_s, bot_s;
    ren.world_to_screen(-0.15, 1.0, left_s, top_s);
    ren.world_to_screen( 0.15, -2.0, right_s, bot_s);
    sph::ColorRGBA wall_color{200, 205, 215, 255};
    ren.draw_line(left_s, -1000, left_s, 2000, wall_color, 2);
    ren.draw_line(right_s, -1000, right_s, 2000, wall_color, 2);

    // Ruler depth marks
    for (double ym = 0.5; ym >= -2.0; ym -= 0.1) {
        int r_sx, r_sy;
        ren.world_to_screen(0.15, ym, r_sx, r_sy);
        ren.draw_line(r_sx, r_sy, r_sx + 10, r_sy, wall_color, 1);
    }

    if (st.mode == 0) {
        // --- MODE A: 2D ODE Simulation & Replay ---

        // Draw shed vortices
        for (const auto& vort : st.shed_vortices) {
            int vsx, vsy;
            ren.world_to_screen(vort.x, vort.y, vsx, vsy);
            uint8_t alpha = static_cast<uint8_t>(std::clamp((vort.life / 2.5) * 160.0, 0.0, 160.0));
            sph::ColorRGBA v_col = (vort.strength > 0) ? sph::ColorRGBA{40, 120, 220, alpha} : sph::ColorRGBA{220, 50, 50, alpha};
            ren.draw_circle_aa(vort.x, vort.y, 0.004, v_col);
        }

        // Draw Fading Wake Ribbon
        if (st.path_trail.size() >= 2) {
            for (size_t i = 1; i < st.path_trail.size(); ++i) {
                int x0, y0, x1, y1;
                ren.world_to_screen(st.path_trail[i - 1].first, st.path_trail[i - 1].second, x0, y0);
                ren.world_to_screen(st.path_trail[i].first, st.path_trail[i].second, x1, y1);

                double frac = static_cast<double>(i) / st.path_trail.size();
                uint8_t a = static_cast<uint8_t>(frac * 180.0);
                ren.draw_line(x0, y0, x1, y1, {70, 130, 210, a}, 2);
            }
        }

        // Draw Ensemble Coins if enabled
        if (st.ensemble_mode) {
            for (const auto& ec : st.ensemble_coins) {
                sph::ColorRGBA ens_fill{100, 150, 200, 40};
                sph::ColorRGBA ens_out{70, 120, 180, 120};
                ren.draw_ellipse(ec.X, ec.Y, ec.a(), ec.b(), ec.theta, ens_fill, ens_out);
            }
        }

        // Draw Primary Coin
        sph::ColorRGBA coin_fill{25, 30, 40, 255};
        sph::ColorRGBA coin_out{10, 10, 15, 255};
        ren.draw_ellipse(st.ode.X, st.ode.Y, st.ode.a(), st.ode.b(), st.ode.theta, coin_fill, coin_out);

        // Draw Live Force and Velocity Vectors
        if (st.show_vectors) {
            int csx, csy;
            ren.world_to_screen(st.ode.X, st.ode.Y, csx, csy);
            double cos_th = std::cos(st.ode.theta);
            double sin_th = std::sin(st.ode.theta);
            double lab_vx = st.ode.u * cos_th - st.ode.v * sin_th;
            double lab_vy = st.ode.u * sin_th + st.ode.v * cos_th;

            // 1. Velocity vector (teal)
            draw_arrow(ren, csx, csy, lab_vx, lab_vy, 120.0, {0, 160, 180, 255});

            // 2. Circulation Lift vector (blue, perpendicular to V)
            draw_arrow(ren, csx, csy, st.FLx, st.FLy, 350.0, {30, 90, 220, 255});

            // 3. Drag vector (red, opposing V)
            draw_arrow(ren, csx, csy, st.FDx, st.FDy, 350.0, {210, 40, 40, 255});

            // 4. Orientation director (dark gray)
            draw_arrow(ren, csx, csy, cos_th * 0.02, sin_th * 0.02, 1000.0, {50, 50, 60, 255});
        }
    } else {
        // --- MODE B: 2D WCSPH Fluid-Structure Interaction ---
        double particle_r = 0.55 * st.sph.sph_cfg.dx;
        for (const auto& p : st.sph.fluid_particles) {
            sph::ColorRGBA c;
            if (st.color_mode_sph == 1) {
                c = sph::SoftwareRenderer::vorticity_to_color(p.vorticity, 40.0);
            } else if (st.color_mode_sph == 2) {
                // Pressure deviation
                double p_dev = p.p - 998.0 * 9.81 * (0.50 - p.pos.y);
                double norm_p = std::clamp(p_dev / 100.0, -1.0, 1.0);
                uint8_t pr = static_cast<uint8_t>(norm_p > 0 ? 255 : 255 + norm_p * 200);
                uint8_t pg = static_cast<uint8_t>(255 - std::abs(norm_p) * 180);
                uint8_t pb = static_cast<uint8_t>(norm_p < 0 ? 255 : 255 - norm_p * 200);
                c = {pr, pg, pb, 220};
            } else {
                c = sph::SoftwareRenderer::speed_to_color(p.vel.length(), 0.5);
            }
            ren.draw_circle_aa(p.pos.x, p.pos.y, particle_r, c);
        }

        // Draw rigid coin
        for (const auto& rb : st.sph.rigid_bodies) {
            sph::ColorRGBA coin_fill{25, 30, 40, 255};
            sph::ColorRGBA coin_out{10, 10, 15, 255};
            ren.draw_ellipse(rb.pos.x, rb.pos.y, rb.config.a(), rb.config.b(), rb.theta, coin_fill, coin_out);
        }
    }

    // Top Honesty Banner in Simulation Viewport
    for (int by = 0; by < 40; ++by) {
        for (int bx = 0; bx < sim_view_w; ++bx) {
            ren.draw_pixel(bx, by, {245, 248, 252, 240});
        }
    }
    ren.draw_line(0, 40, sim_view_w, 40, {210, 220, 235, 255}, 1);

    std::string honesty_banner = (st.mode == 0)
        ? "MODE A: 2D Quasi-Steady ODE Numerical Simulation (Andersen 2005b)"
        : "MODE B: 2D WCSPH-FSI Numerical Simulation (Wendland C2 + Akinci Coupling)";
    ren.draw_string(15, 12, honesty_banner, {20, 60, 120, 255}, 2);

    // Vector Legend in Simulation Viewport
    if (st.mode == 0 && st.show_vectors) {
        int leg_y = 52;
        ren.draw_line(15, leg_y + 8, 35, leg_y + 8, {0, 160, 180, 255}, 2);
        ren.draw_string(42, leg_y + 4, "Velocity V", {60, 70, 80, 255}, 1);

        ren.draw_line(135, leg_y + 8, 155, leg_y + 8, {30, 90, 220, 255}, 2);
        ren.draw_string(162, leg_y + 4, "Circulation Lift F_L", {60, 70, 80, 255}, 1);

        ren.draw_line(295, leg_y + 8, 315, leg_y + 8, {210, 40, 40, 255}, 2);
        ren.draw_string(322, leg_y + 4, "Viscous Drag F_D", {60, 70, 80, 255}, 1);
    }

    // --- RIGHT SIDE: TELEMETRY HUD & SYNCHRONIZED STRIP CHARTS ---
    ren.draw_line(hud_view_x, 0, hud_view_x, ren.height, {220, 225, 235, 255}, 2);
    for (int y = 0; y < ren.height; ++y) {
        for (int x = hud_view_x + 1; x < ren.width; ++x) {
            ren.draw_pixel(x, y, {252, 253, 255, 255});
        }
    }

    // Panel Header
    ren.draw_string(hud_view_x + 15, 15, "AUTUMN COIN TELEMETRY", {20, 45, 90, 255}, 2);

    // Live Regime Badge
    std::string badge = st.get_regime_badge();
    sph::ColorRGBA badge_bg = {235, 243, 255, 255};
    sph::ColorRGBA badge_tx = {25, 75, 160, 255};
    if (badge == "STEADY") { badge_bg = {235, 248, 235, 255}; badge_tx = {30, 120, 50, 255}; }
    else if (badge == "TUMBLING") { badge_bg = {255, 240, 235, 255}; badge_tx = {180, 50, 30, 255}; }
    else if (badge == "MIXED / CHAOTIC") { badge_bg = {255, 248, 230, 255}; badge_tx = {190, 100, 20, 255}; }

    for (int by = 42; by < 66; ++by) {
        for (int bx = hud_view_x + 15; bx < hud_view_x + 220; ++bx) {
            ren.draw_pixel(bx, by, badge_bg);
        }
    }
    ren.draw_string(hud_view_x + 25, 48, "REGIME: " + badge, badge_tx, 1);

    // Telemetry Numbers
    double cur_t = (st.mode == 0) ? st.ode.sim_time : st.sph.sim_time;
    double cur_X_mm = (st.mode == 0) ? st.ode.X * 1000.0 : (st.sph.rigid_bodies.empty() ? 0.0 : st.sph.rigid_bodies[0].pos.x * 1000.0);
    double cur_Y_mm = (st.mode == 0) ? st.ode.Y * 1000.0 : (st.sph.rigid_bodies.empty() ? 0.0 : st.sph.rigid_bodies[0].pos.y * 1000.0);
    double cur_th_deg = (st.mode == 0) ? st.ode.theta * 180.0 / M_PI : (st.sph.rigid_bodies.empty() ? 0.0 : st.sph.rigid_bodies[0].theta * 180.0 / M_PI);
    double cur_om = (st.mode == 0) ? st.ode.omega : (st.sph.rigid_bodies.empty() ? 0.0 : st.sph.rigid_bodies[0].omega);
    double cur_speed = (st.mode == 0) ? std::hypot(st.ode.u, st.ode.v) : (st.sph.rigid_bodies.empty() ? 0.0 : st.sph.rigid_bodies[0].vel.length());
    double cur_Rein = (st.mode == 0) ? (998.0 * std::sqrt(std::max(st.ode.rho_s/998.0 - 1.0, 0.0) * 9.81 * st.ode.h) * st.ode.L / st.current_mu) : 0.0;

    std::vector<std::string> metrics = {
        "Time t:       " + std::to_string(cur_t).substr(0, 5) + " s",
        "Position:     (" + std::to_string(static_cast<int>(cur_X_mm)) + ", " + std::to_string(static_cast<int>(cur_Y_mm)) + ") mm",
        "Tilt theta:   " + std::to_string(cur_th_deg).substr(0, 5) + " deg",
        "Spin omega:   " + std::to_string(cur_om).substr(0, 5) + " rad/s",
        "Speed |V|:    " + std::to_string(cur_speed).substr(0, 5) + " m/s",
        "Inertia I*:   " + std::to_string(st.current_I_star).substr(0, 5),
        "Re_in:        " + std::to_string(static_cast<int>(cur_Rein)),
        "Viscosity mu: " + std::to_string(st.current_mu).substr(0, 6) + " Pa.s",
    };

    int ty = 80;
    for (const auto& line : metrics) {
        ren.draw_string(hud_view_x + 15, ty, line, {50, 60, 75, 255}, 1);
        ty += 16;
    }

    // Mini-Map of Water Tank
    int mm_x = hud_view_x + 250;
    int mm_y = 45;
    int mm_w = 140;
    int mm_h = 160;
    for (int y = mm_y; y < mm_y + mm_h; ++y) {
        for (int x = mm_x; x < mm_x + mm_w; ++x) {
            ren.draw_pixel(x, y, {240, 244, 250, 255});
        }
    }
    ren.draw_line(mm_x, mm_y, mm_x + mm_w, mm_y, {200, 210, 225, 255}, 1);
    ren.draw_line(mm_x, mm_y + mm_h, mm_x + mm_w, mm_y + mm_h, {200, 210, 225, 255}, 1);
    ren.draw_line(mm_x, mm_y, mm_x, mm_y + mm_h, {200, 210, 225, 255}, 1);
    ren.draw_line(mm_x + mm_w, mm_y, mm_x + mm_w, mm_y + mm_h, {200, 210, 225, 255}, 1);
    ren.draw_string(mm_x + 20, mm_y + 6, "FULL TANK MAP", {120, 135, 155, 255}, 1);

    // Mini-map coin marker
    double norm_x = std::clamp((cam_x + 0.15) / 0.30, 0.0, 1.0);
    double norm_y = std::clamp((0.50 - cam_y) / 2.5, 0.0, 1.0);
    int coin_mm_x = mm_x + static_cast<int>(norm_x * mm_w);
    int coin_mm_y = mm_y + static_cast<int>(norm_y * mm_h);
    ren.draw_circle_aa(cam_x, cam_y, 0.003, {220, 50, 50, 255}); // will clip to world view, draw manually
    for (int dy = -3; dy <= 3; ++dy) {
        for (int dx = -3; dx <= 3; ++dx) {
            if (dx * dx + dy * dy <= 9) {
                ren.draw_pixel(coin_mm_x + dx, coin_mm_y + dy, {220, 50, 50, 255});
            }
        }
    }

    // Synchronized Strip Charts
    // Top Chart: theta(t)
    int chart1_y = 220;
    int chart_w = 380;
    int chart_h = 130;
    ren.draw_string(hud_view_x + 15, chart1_y, "TILT ANGLE theta(t) [deg]", {30, 50, 80, 255}, 1);
    chart1_y += 18;

    for (int y = chart1_y; y < chart1_y + chart_h; ++y) {
        for (int x = hud_view_x + 15; x < hud_view_x + 15 + chart_w; ++x) {
            ren.draw_pixel(x, y, {248, 250, 254, 255});
        }
    }
    ren.draw_line(hud_view_x + 15, chart1_y + chart_h / 2, hud_view_x + 15 + chart_w, chart1_y + chart_h / 2, {215, 225, 238, 255}, 1); // 0 deg line

    if (st.history_theta.size() >= 2) {
        for (size_t i = 1; i < st.history_theta.size(); ++i) {
            int cx0 = hud_view_x + 15 + static_cast<int>((static_cast<double>(i - 1) / st.history_theta.size()) * chart_w);
            int cx1 = hud_view_x + 15 + static_cast<int>((static_cast<double>(i) / st.history_theta.size()) * chart_w);
            double th0_deg = st.history_theta[i - 1] * 180.0 / M_PI;
            double th1_deg = st.history_theta[i] * 180.0 / M_PI;
            int cy0 = chart1_y + chart_h / 2 - static_cast<int>(std::clamp(th0_deg / 180.0, -1.0, 1.0) * (chart_h * 0.45));
            int cy1 = chart1_y + chart_h / 2 - static_cast<int>(std::clamp(th1_deg / 180.0, -1.0, 1.0) * (chart_h * 0.45));
            ren.draw_line(cx0, cy0, cx1, cy1, {40, 110, 210, 255}, 2);
        }
    }

    // Bottom Chart: Speed |V(t)| and |v_Y(t)|
    int chart2_y = chart1_y + chart_h + 20;
    ren.draw_string(hud_view_x + 15, chart2_y, "DESCENT SPEED |V(t)| & |v_Y| [m/s]", {30, 50, 80, 255}, 1);
    chart2_y += 18;

    for (int y = chart2_y; y < chart2_y + chart_h; ++y) {
        for (int x = hud_view_x + 15; x < hud_view_x + 15 + chart_w; ++x) {
            ren.draw_pixel(x, y, {248, 250, 254, 255});
        }
    }

    if (st.history_speed.size() >= 2) {
        for (size_t i = 1; i < st.history_speed.size(); ++i) {
            int cx0 = hud_view_x + 15 + static_cast<int>((static_cast<double>(i - 1) / st.history_speed.size()) * chart_w);
            int cx1 = hud_view_x + 15 + static_cast<int>((static_cast<double>(i) / st.history_speed.size()) * chart_w);
            int cy0 = chart2_y + chart_h - static_cast<int>(std::clamp(st.history_speed[i - 1] / 0.8, 0.0, 1.0) * (chart_h * 0.90));
            int cy1 = chart2_y + chart_h - static_cast<int>(std::clamp(st.history_speed[i] / 0.8, 0.0, 1.0) * (chart_h * 0.90));
            ren.draw_line(cx0, cy0, cx1, cy1, {220, 80, 40, 255}, 2);

            // vertical velocity vy
            int vy0 = chart2_y + chart_h - static_cast<int>(std::clamp(st.history_vy[i - 1] / 0.8, 0.0, 1.0) * (chart_h * 0.90));
            int vy1 = chart2_y + chart_h - static_cast<int>(std::clamp(st.history_vy[i] / 0.8, 0.0, 1.0) * (chart_h * 0.90));
            ren.draw_line(cx0, vy0, cx1, vy1, {60, 170, 100, 255}, 1);
        }
    }

    // Keyboard Shortcuts & Controls Guide at Bottom of HUD
    int ky = chart2_y + chart_h + 20;
    ren.draw_string(hud_view_x + 15, ky, "INTERACTIVE CONTROLS:", {20, 40, 80, 255}, 1);
    ky += 16;
    std::vector<std::string> keys = {
        "[Tab] Toggle Mode A (ODE) / B (SPH)",
        "[1] Steady  [2] Flutter  [3] Tumble  [4] Mixed",
        "[Space] Pause/Play    [S] Step Frame",
        "[R] Reset Drop         [E] Ensemble (15 Coins)",
        "[C] Cycle SPH Ramp     [P] Screenshot PNG",
    };
    for (const auto& kline : keys) {
        ren.draw_string(hud_view_x + 15, ky, kline, {80, 95, 115, 255}, 1);
        ky += 15;
    }
}

// Window Procedure for native Win32 Desktop Window
static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_KEYDOWN: {
            switch (wParam) {
                case VK_TAB:
                    g_state.mode = (g_state.mode == 0) ? 1 : 0;
                    if (g_state.mode == 1 && !g_state.sph_initialized) {
                        g_state.init_sph();
                    }
                    break;
                case '1':
                    g_state.current_I_star = 0.06;
                    g_state.current_theta0_deg = 5.0;
                    g_state.init_ode();
                    if (g_state.mode == 1) g_state.init_sph();
                    break;
                case '2':
                    g_state.current_I_star = 0.68;
                    g_state.current_theta0_deg = 5.0;
                    g_state.init_ode();
                    if (g_state.mode == 1) g_state.init_sph();
                    break;
                case '3':
                    g_state.current_I_star = 1.20;
                    g_state.current_theta0_deg = 15.0;
                    g_state.init_ode();
                    if (g_state.mode == 1) g_state.init_sph();
                    break;
                case '4':
                    g_state.current_I_star = 3.50;
                    g_state.current_theta0_deg = 45.0;
                    g_state.init_ode();
                    if (g_state.mode == 1) g_state.init_sph();
                    break;
                case VK_SPACE:
                    g_state.paused = !g_state.paused;
                    break;
                case 'S':
                    if (g_state.paused) {
                        // Advance one sub-step
                        if (g_state.mode == 0) {
                            g_state.ode.step(0.016, g_state.FLx, g_state.FLy, g_state.FDx, g_state.FDy);
                        } else if (g_state.sph_initialized) {
                            g_state.sph.step_kdk(g_state.sph.sph_cfg.dt);
                        }
                    }
                    break;
                case 'R':
                    g_state.init_ode();
                    if (g_state.mode == 1) g_state.init_sph();
                    break;
                case 'C':
                    g_state.color_mode_sph = (g_state.color_mode_sph + 1) % 3;
                    break;
                case 'E':
                    g_state.ensemble_mode = !g_state.ensemble_mode;
                    g_state.init_ode();
                    break;
                case 'P': {
                    std::string fname = "results_sph/frames/screenshot_" + std::to_string(static_cast<int>(time(nullptr))) + ".png";
                    g_renderer.save_png(fname);
                    std::cout << "[Visualizer] Screenshot saved to: " << fname << std::endl;
                    break;
                }
                case VK_ESCAPE:
                    PostQuitMessage(0);
                    break;
            }
            InvalidateRect(hwnd, NULL, FALSE);
            break;
        }
        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hwnd, &ps);

            BITMAPINFO bmi = {0};
            bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
            bmi.bmiHeader.biWidth = g_renderer.width;
            bmi.bmiHeader.biHeight = -g_renderer.height; // Top-down
            bmi.bmiHeader.biPlanes = 1;
            bmi.bmiHeader.biBitCount = 32;
            bmi.bmiHeader.biCompression = BI_RGB;

            // Invert R and B for Win32 BGRA format
            std::vector<uint8_t> bgra = g_renderer.pixels;
            for (size_t i = 0; i < bgra.size(); i += 4) {
                std::swap(bgra[i], bgra[i + 2]);
            }

            SetDIBitsToDevice(hdc, 0, 0, g_renderer.width, g_renderer.height,
                             0, 0, 0, g_renderer.height,
                             bgra.data(), &bmi, DIB_RGB_COLORS);

            EndPaint(hwnd, &ps);
            break;
        }
        case WM_DESTROY:
            PostQuitMessage(0);
            break;
        default:
            return DefWindowProc(hwnd, msg, wParam, lParam);
    }
    return 0;
}

int main(int argc, char** argv) {
    std::cout << "========================================================\n";
    std::cout << "   AUTUMN COIN: REAL-TIME 2D PHYSICS VISUALIZER         \n";
    std::cout << "   Mode A: Quasi-Steady ODE | Mode B: WCSPH-FSI         \n";
    std::cout << "========================================================\n";

    g_state.init_ode();

    // Check if running in headless / export mode
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--export-four-frames") {
            std::cout << "[Visualizer] Exporting 4 publication benchmark frames...\n";
            // 1. Steady
            g_state.mode = 0;
            g_state.current_I_star = 0.06;
            g_state.current_theta0_deg = 5.0;
            g_state.init_ode();
            for (int f = 0; f < 300; ++f) {
                g_state.ode.step(0.005, g_state.FLx, g_state.FLy, g_state.FDx, g_state.FDy);
                g_state.path_trail.push_back({g_state.ode.X, g_state.ode.Y});
                g_state.history_theta.push_back(g_state.ode.theta);
                g_state.history_speed.push_back(std::hypot(g_state.ode.u, g_state.ode.v));
                g_state.history_vy.push_back(std::abs(g_state.ode.u * std::sin(g_state.ode.theta) + g_state.ode.v * std::cos(g_state.ode.theta)));
            }
            render_visualizer_frame(g_renderer, g_state);
            g_renderer.save_png("results_sph/frames/frame_steady.png");
            std::cout << "  -> results_sph/frames/frame_steady.png\n";

            // 2. Flutter
            g_state.current_I_star = 0.68;
            g_state.current_theta0_deg = 5.0;
            g_state.init_ode();
            for (int f = 0; f < 400; ++f) {
                g_state.ode.step(0.005, g_state.FLx, g_state.FLy, g_state.FDx, g_state.FDy);
                g_state.path_trail.push_back({g_state.ode.X, g_state.ode.Y});
                g_state.history_theta.push_back(g_state.ode.theta);
                g_state.history_speed.push_back(std::hypot(g_state.ode.u, g_state.ode.v));
                g_state.history_vy.push_back(std::abs(g_state.ode.u * std::sin(g_state.ode.theta) + g_state.ode.v * std::cos(g_state.ode.theta)));
                // vortex shedding at turning point
                if (f > 10 && ((g_state.prev_omega > 0 && g_state.ode.omega <= 0) || (g_state.prev_omega < 0 && g_state.ode.omega >= 0))) {
                    g_state.shed_vortices.push_back({g_state.ode.X, g_state.ode.Y, (g_state.prev_omega > 0 ? 1.0 : -1.0), 2.5});
                }
                g_state.prev_omega = g_state.ode.omega;
            }
            render_visualizer_frame(g_renderer, g_state);
            g_renderer.save_png("results_sph/frames/frame_flutter.png");
            std::cout << "  -> results_sph/frames/frame_flutter.png\n";

            // 3. Tumble
            g_state.current_I_star = 1.20;
            g_state.current_theta0_deg = 15.0;
            g_state.init_ode();
            for (int f = 0; f < 450; ++f) {
                g_state.ode.step(0.005, g_state.FLx, g_state.FLy, g_state.FDx, g_state.FDy);
                g_state.path_trail.push_back({g_state.ode.X, g_state.ode.Y});
                g_state.history_theta.push_back(g_state.ode.theta);
                g_state.history_speed.push_back(std::hypot(g_state.ode.u, g_state.ode.v));
                g_state.history_vy.push_back(std::abs(g_state.ode.u * std::sin(g_state.ode.theta) + g_state.ode.v * std::cos(g_state.ode.theta)));
            }
            render_visualizer_frame(g_renderer, g_state);
            g_renderer.save_png("results_sph/frames/frame_tumble.png");
            std::cout << "  -> results_sph/frames/frame_tumble.png\n";

            // 4. SPH Vorticity
            g_state.mode = 1;
            g_state.color_mode_sph = 1; // vorticity
            g_state.current_I_star = 1.20;
            g_state.init_sph();
            for (int f = 0; f < 120; ++f) {
                g_state.sph.step_kdk(g_state.sph.sph_cfg.dt);
            }
            render_visualizer_frame(g_renderer, g_state);
            g_renderer.save_png("results_sph/frames/frame_vorticity_sph.png");
            std::cout << "  -> results_sph/frames/frame_vorticity_sph.png\n";
            std::cout << "[Visualizer] All 4 frames exported successfully.\n";
            return 0;
        }
    }

    // Register Win32 Window Class
    HINSTANCE hInstance = GetModuleHandle(NULL);
    WNDCLASSEX wc = {0};
    wc.cbSize = sizeof(WNDCLASSEX);
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.lpszClassName = "AutumnCoinVisualizerClass";

    if (!RegisterClassEx(&wc)) {
        std::cerr << "[Error] Failed to register Win32 window class.\n";
        return 1;
    }

    RECT wr = {0, 0, g_renderer.width, g_renderer.height};
    AdjustWindowRect(&wr, WS_OVERLAPPEDWINDOW, FALSE);

    HWND hwnd = CreateWindowEx(
        0,
        wc.lpszClassName,
        "Autumn Coin 2D Real-Time Physics Visualizer (Sebastian Lague Style)",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT,
        wr.right - wr.left, wr.bottom - wr.top,
        NULL, NULL, hInstance, NULL
    );

    if (!hwnd) {
        std::cerr << "[Error] Failed to create Win32 window.\n";
        return 1;
    }

    ShowWindow(hwnd, SW_SHOW);
    UpdateWindow(hwnd);

    std::cout << "[Visualizer] Window created. Running 60 FPS simulation loop...\n";

    // Main 60 FPS loop
    MSG msg = {0};
    auto last_time = std::chrono::high_resolution_clock::now();

    while (msg.message != WM_QUIT) {
        if (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        } else {
            auto now = std::chrono::high_resolution_clock::now();
            double dt_frame = std::chrono::duration<double>(now - last_time).count();

            if (dt_frame >= 1.0 / 60.0) {
                last_time = now;

                if (!g_state.paused) {
                    if (g_state.mode == 0) {
                        // Sub-step ODE for numerical precision
                        for (int sub = 0; sub < 4; ++sub) {
                            g_state.ode.step((1.0 / 240.0) * g_state.playback_speed,
                                             g_state.FLx, g_state.FLy, g_state.FDx, g_state.FDy);

                            if (g_state.ensemble_mode) {
                                for (auto& ec : g_state.ensemble_coins) {
                                    double d1, d2, d3, d4;
                                    ec.step((1.0 / 240.0) * g_state.playback_speed, d1, d2, d3, d4);
                                }
                            }
                        }

                        // Vortex shedding check
                        if ((g_state.prev_omega > 0 && g_state.ode.omega <= 0) ||
                            (g_state.prev_omega < 0 && g_state.ode.omega >= 0)) {
                            g_state.shed_vortices.push_back({g_state.ode.X, g_state.ode.Y, (g_state.prev_omega > 0 ? 1.0 : -1.0), 2.5});
                        }
                        g_state.prev_omega = g_state.ode.omega;

                        // Age vortices
                        for (auto& v : g_state.shed_vortices) {
                            v.life -= (1.0 / 60.0);
                        }
                        g_state.shed_vortices.erase(
                            std::remove_if(g_state.shed_vortices.begin(), g_state.shed_vortices.end(),
                                           [](const sph::SyntheticVortex& v) { return v.life <= 0.0; }),
                            g_state.shed_vortices.end()
                        );

                        // Record history
                        g_state.path_trail.push_back({g_state.ode.X, g_state.ode.Y});
                        if (g_state.path_trail.size() > 400) g_state.path_trail.pop_front();

                        g_state.history_theta.push_back(g_state.ode.theta);
                        if (g_state.history_theta.size() > 250) g_state.history_theta.pop_front();

                        g_state.history_speed.push_back(std::hypot(g_state.ode.u, g_state.ode.v));
                        if (g_state.history_speed.size() > 250) g_state.history_speed.pop_front();

                        double vy = std::abs(g_state.ode.u * std::sin(g_state.ode.theta) + g_state.ode.v * std::cos(g_state.ode.theta));
                        g_state.history_vy.push_back(vy);
                        if (g_state.history_vy.size() > 250) g_state.history_vy.pop_front();

                    } else if (g_state.sph_initialized) {
                        for (int sub = 0; sub < 2; ++sub) {
                            g_state.sph.step_kdk(g_state.sph.sph_cfg.dt);
                        }
                    }
                }

                // Render frame
                render_visualizer_frame(g_renderer, g_state);

                // Redraw window
                HDC hdc = GetDC(hwnd);
                BITMAPINFO bmi = {0};
                bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
                bmi.bmiHeader.biWidth = g_renderer.width;
                bmi.bmiHeader.biHeight = -g_renderer.height;
                bmi.bmiHeader.biPlanes = 1;
                bmi.bmiHeader.biBitCount = 32;
                bmi.bmiHeader.biCompression = BI_RGB;

                std::vector<uint8_t> bgra = g_renderer.pixels;
                for (size_t i = 0; i < bgra.size(); i += 4) {
                    std::swap(bgra[i], bgra[i + 2]);
                }

                SetDIBitsToDevice(hdc, 0, 0, g_renderer.width, g_renderer.height,
                                 0, 0, 0, g_renderer.height,
                                 bgra.data(), &bmi, DIB_RGB_COLORS);
                ReleaseDC(hwnd, hdc);
            } else {
                Sleep(1);
            }
        }
    }

    return 0;
}
