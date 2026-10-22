#pragma once

#include "config.hpp"
#include "sph_solver.hpp"
#include <vector>
#include <string>
#include <cstdint>

namespace sph {

struct ColorRGBA {
    uint8_t r = 255;
    uint8_t g = 255;
    uint8_t b = 255;
    uint8_t a = 255;
};

class SoftwareRenderer {
public:
    int width = 960;
    int height = 1280;
    double ppm = 2000.0; // Pixels per meter
    Vec2 center_world = {0.0, -0.15}; // World coordinates at canvas center
    std::vector<uint8_t> pixels; // RGBA 4 bytes per pixel

    std::vector<Vec2> coin_trail;

    SoftwareRenderer(int w = 960, int h = 1280, double pixels_per_meter = 2000.0);

    void set_view(double world_center_x, double world_center_y, double pixels_per_meter);
    void clear(ColorRGBA bg_color = {255, 255, 255, 255});

    // World to screen mapping
    void world_to_screen(double wx, double wy, int& sx, int& sy) const;

    // Drawing primitives
    void draw_pixel(int sx, int sy, ColorRGBA c);
    void draw_circle_aa(double wx, double wy, double radius_m, ColorRGBA c);
    void draw_line(int x0, int y0, int x1, int y1, ColorRGBA c, int thickness = 1);
    void draw_ellipse(double cx, double cy, double a, double b, double theta, ColorRGBA fill, ColorRGBA outline);
    void draw_string(int sx, int sy, const std::string& text, ColorRGBA color, int scale = 2);

    // Color ramps
    static ColorRGBA speed_to_color(double speed, double max_speed = 0.5);
    static ColorRGBA vorticity_to_color(double omega_z, double max_vort = 50.0);

    // Scene rendering
    void render_sph_frame(const SPHSolver& solver,
                          const std::string& mode_label,
                          const std::string& color_mode,
                          double max_field_val);

    void render_ode_replay_frame(const Vec2& coin_pos,
                                 double theta,
                                 double L,
                                 double h,
                                 double t,
                                 double I_star,
                                 double Re_meas,
                                 const std::string& regime_label);

    bool save_png(const std::string& filepath) const;
};

} // namespace sph
