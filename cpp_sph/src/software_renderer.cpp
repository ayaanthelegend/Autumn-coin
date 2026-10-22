#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#include "software_renderer.hpp"
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <sstream>

namespace sph {

// Compact 5x7 ASCII font bitmap (ASCII 32 to 126)
static const uint8_t font5x7[95][5] = {
    {0x00, 0x00, 0x00, 0x00, 0x00}, // 32 ' '
    {0x00, 0x00, 0x5F, 0x00, 0x00}, // 33 '!'
    {0x00, 0x07, 0x00, 0x07, 0x00}, // 34 '"'
    {0x14, 0x7F, 0x14, 0x7F, 0x14}, // 35 '#'
    {0x24, 0x2A, 0x7F, 0x2A, 0x12}, // 36 '$'
    {0x23, 0x13, 0x08, 0x64, 0x62}, // 37 '%'
    {0x36, 0x49, 0x55, 0x22, 0x50}, // 38 '&'
    {0x00, 0x05, 0x03, 0x00, 0x00}, // 39 '\''
    {0x00, 0x1C, 0x22, 0x41, 0x00}, // 40 '('
    {0x00, 0x41, 0x22, 0x1C, 0x00}, // 41 ')'
    {0x14, 0x08, 0x3E, 0x08, 0x14}, // 42 '*'
    {0x08, 0x08, 0x3E, 0x08, 0x08}, // 43 '+'
    {0x00, 0x50, 0x30, 0x00, 0x00}, // 44 ','
    {0x08, 0x08, 0x08, 0x08, 0x08}, // 45 '-'
    {0x00, 0x60, 0x60, 0x00, 0x00}, // 46 '.'
    {0x20, 0x10, 0x08, 0x04, 0x02}, // 47 '/'
    {0x3E, 0x51, 0x49, 0x45, 0x3E}, // 48 '0'
    {0x00, 0x42, 0x7F, 0x40, 0x00}, // 49 '1'
    {0x42, 0x61, 0x51, 0x49, 0x46}, // 50 '2'
    {0x21, 0x41, 0x45, 0x4B, 0x31}, // 51 '3'
    {0x18, 0x14, 0x12, 0x7F, 0x10}, // 52 '4'
    {0x27, 0x45, 0x45, 0x45, 0x39}, // 53 '5'
    {0x3C, 0x4A, 0x49, 0x49, 0x30}, // 54 '6'
    {0x01, 0x71, 0x09, 0x05, 0x03}, // 55 '7'
    {0x36, 0x49, 0x49, 0x49, 0x36}, // 56 '8'
    {0x06, 0x49, 0x49, 0x29, 0x1E}, // 57 '9'
    {0x00, 0x36, 0x36, 0x00, 0x00}, // 58 ':'
    {0x00, 0x56, 0x36, 0x00, 0x00}, // 59 ';'
    {0x08, 0x14, 0x22, 0x41, 0x00}, // 60 '<'
    {0x14, 0x14, 0x14, 0x14, 0x14}, // 61 '='
    {0x00, 0x41, 0x22, 0x14, 0x08}, // 62 '>'
    {0x02, 0x01, 0x51, 0x09, 0x06}, // 63 '?'
    {0x32, 0x49, 0x79, 0x41, 0x3E}, // 64 '@'
    {0x7E, 0x11, 0x11, 0x11, 0x7E}, // 65 'A'
    {0x7F, 0x49, 0x49, 0x49, 0x36}, // 66 'B'
    {0x3E, 0x41, 0x41, 0x41, 0x22}, // 67 'C'
    {0x7F, 0x41, 0x41, 0x22, 0x1C}, // 68 'D'
    {0x7F, 0x49, 0x49, 0x49, 0x41}, // 69 'E'
    {0x7F, 0x09, 0x09, 0x09, 0x01}, // 70 'F'
    {0x3E, 0x41, 0x49, 0x49, 0x7A}, // 71 'G'
    {0x7F, 0x08, 0x08, 0x08, 0x7F}, // 72 'H'
    {0x00, 0x41, 0x7F, 0x41, 0x00}, // 73 'I'
    {0x20, 0x40, 0x41, 0x3F, 0x01}, // 74 'J'
    {0x7F, 0x08, 0x14, 0x22, 0x41}, // 75 'K'
    {0x7F, 0x40, 0x40, 0x40, 0x40}, // 76 'L'
    {0x7F, 0x02, 0x0C, 0x02, 0x7F}, // 77 'M'
    {0x7F, 0x04, 0x08, 0x10, 0x7F}, // 78 'N'
    {0x3E, 0x41, 0x41, 0x41, 0x3E}, // 79 'O'
    {0x7F, 0x09, 0x09, 0x09, 0x06}, // 80 'P'
    {0x3E, 0x41, 0x51, 0x21, 0x5E}, // 81 'Q'
    {0x7F, 0x09, 0x19, 0x29, 0x46}, // 82 'R'
    {0x46, 0x49, 0x49, 0x49, 0x31}, // 83 'S'
    {0x01, 0x01, 0x7F, 0x01, 0x01}, // 84 'T'
    {0x3F, 0x40, 0x40, 0x40, 0x3F}, // 85 'U'
    {0x1F, 0x20, 0x40, 0x20, 0x1F}, // 86 'V'
    {0x3F, 0x40, 0x38, 0x40, 0x3F}, // 87 'W'
    {0x63, 0x14, 0x08, 0x14, 0x63}, // 88 'X'
    {0x07, 0x08, 0x70, 0x08, 0x07}, // 89 'Y'
    {0x61, 0x51, 0x49, 0x45, 0x43}, // 90 'Z'
    {0x00, 0x7F, 0x41, 0x41, 0x00}, // 91 '['
    {0x02, 0x04, 0x08, 0x10, 0x20}, // 92 '\'
    {0x00, 0x41, 0x41, 0x7F, 0x00}, // 93 ']'
    {0x04, 0x02, 0x01, 0x02, 0x04}, // 94 '^'
    {0x40, 0x40, 0x40, 0x40, 0x40}, // 95 '_'
    {0x00, 0x01, 0x02, 0x04, 0x00}, // 96 '`'
    {0x20, 0x54, 0x54, 0x54, 0x78}, // 97 'a'
    {0x7F, 0x48, 0x44, 0x44, 0x38}, // 98 'b'
    {0x38, 0x44, 0x44, 0x44, 0x20}, // 99 'c'
    {0x38, 0x44, 0x44, 0x48, 0x7F}, // 100 'd'
    {0x38, 0x54, 0x54, 0x54, 0x18}, // 101 'e'
    {0x08, 0x7E, 0x09, 0x01, 0x02}, // 102 'f'
    {0x08, 0x54, 0x54, 0x54, 0x3C}, // 103 'g'
    {0x7F, 0x08, 0x04, 0x04, 0x78}, // 104 'h'
    {0x00, 0x44, 0x7D, 0x40, 0x00}, // 105 'i'
    {0x20, 0x40, 0x44, 0x3D, 0x00}, // 106 'j'
    {0x7F, 0x10, 0x28, 0x44, 0x00}, // 107 'k'
    {0x00, 0x41, 0x7F, 0x40, 0x00}, // 108 'l'
    {0x7C, 0x04, 0x18, 0x04, 0x78}, // 109 'm'
    {0x7C, 0x08, 0x04, 0x04, 0x78}, // 110 'n'
    {0x38, 0x44, 0x44, 0x44, 0x38}, // 111 'o'
    {0x7C, 0x14, 0x14, 0x14, 0x08}, // 112 'p'
    {0x08, 0x14, 0x14, 0x18, 0x7C}, // 113 'q'
    {0x7C, 0x08, 0x04, 0x04, 0x08}, // 114 'r'
    {0x48, 0x54, 0x54, 0x54, 0x20}, // 115 's'
    {0x04, 0x3F, 0x44, 0x40, 0x20}, // 116 't'
    {0x3C, 0x40, 0x40, 0x20, 0x7C}, // 117 'u'
    {0x1C, 0x20, 0x40, 0x20, 0x1C}, // 118 'v'
    {0x3C, 0x40, 0x30, 0x40, 0x3C}, // 119 'w'
    {0x44, 0x28, 0x10, 0x28, 0x44}, // 120 'x'
    {0x0C, 0x50, 0x50, 0x50, 0x3C}, // 121 'y'
    {0x44, 0x64, 0x54, 0x4C, 0x44}, // 122 'z'
    {0x00, 0x08, 0x36, 0x41, 0x00}, // 123 '{'
    {0x00, 0x00, 0x7F, 0x00, 0x00}, // 124 '|'
    {0x00, 0x41, 0x36, 0x08, 0x00}, // 125 '}'
    {0x08, 0x08, 0x2A, 0x1C, 0x08}  // 126 '~'
};

SoftwareRenderer::SoftwareRenderer(int w, int h, double pixels_per_meter)
    : width(w), height(h), ppm(pixels_per_meter) {
    pixels.assign(width * height * 4, 255);
}

void SoftwareRenderer::set_view(double world_center_x, double world_center_y, double pixels_per_meter) {
    center_world = {world_center_x, world_center_y};
    ppm = pixels_per_meter;
}

void SoftwareRenderer::clear(ColorRGBA bg_color) {
    for (size_t i = 0; i < pixels.size(); i += 4) {
        pixels[i + 0] = bg_color.r;
        pixels[i + 1] = bg_color.g;
        pixels[i + 2] = bg_color.b;
        pixels[i + 3] = bg_color.a;
    }
}

void SoftwareRenderer::world_to_screen(double wx, double wy, int& sx, int& sy) const {
    double cx = width * 0.5;
    double cy = height * 0.5;
    sx = static_cast<int>(std::round(cx + (wx - center_world.x) * ppm));
    sy = static_cast<int>(std::round(cy - (wy - center_world.y) * ppm)); // Invert Y
}

void SoftwareRenderer::draw_pixel(int sx, int sy, ColorRGBA c) {
    if (sx < 0 || sx >= width || sy < 0 || sy >= height) return;
    int idx = (sy * width + sx) * 4;
    // Simple alpha blend over existing color
    if (c.a == 255) {
        pixels[idx + 0] = c.r;
        pixels[idx + 1] = c.g;
        pixels[idx + 2] = c.b;
        pixels[idx + 3] = 255;
    } else {
        float a = c.a / 255.0f;
        float inv_a = 1.0f - a;
        pixels[idx + 0] = static_cast<uint8_t>(c.r * a + pixels[idx + 0] * inv_a);
        pixels[idx + 1] = static_cast<uint8_t>(c.g * a + pixels[idx + 1] * inv_a);
        pixels[idx + 2] = static_cast<uint8_t>(c.b * a + pixels[idx + 2] * inv_a);
        pixels[idx + 3] = 255;
    }
}

void SoftwareRenderer::draw_circle_aa(double wx, double wy, double radius_m, ColorRGBA c) {
    int sx, sy;
    world_to_screen(wx, wy, sx, sy);
    double r_px = radius_m * ppm;
    int r_ceil = static_cast<int>(std::ceil(r_px)) + 1;

    for (int dy = -r_ceil; dy <= r_ceil; ++dy) {
        int py = sy + dy;
        if (py < 0 || py >= height) continue;
        for (int dx = -r_ceil; dx <= r_ceil; ++dx) {
            int px = sx + dx;
            if (px < 0 || px >= width) continue;

            double dist = std::sqrt(dx * dx + dy * dy);
            if (dist <= r_px - 0.5) {
                draw_pixel(px, py, c);
            } else if (dist < r_px + 0.5) {
                double frac = (r_px + 0.5 - dist);
                ColorRGBA blend = c;
                blend.a = static_cast<uint8_t>(std::clamp(c.a * frac, 0.0, 255.0));
                draw_pixel(px, py, blend);
            }
        }
    }
}

void SoftwareRenderer::draw_line(int x0, int y0, int x1, int y1, ColorRGBA c, int thickness) {
    int dx = std::abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -std::abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy, e2;

    while (true) {
        for (int ty = -thickness / 2; ty <= thickness / 2; ++ty) {
            for (int tx = -thickness / 2; tx <= thickness / 2; ++tx) {
                draw_pixel(x0 + tx, y0 + ty, c);
            }
        }
        if (x0 == x1 && y0 == y1) break;
        e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

void SoftwareRenderer::draw_ellipse(double cx, double cy, double a, double b, double theta, ColorRGBA fill, ColorRGBA outline) {
    int scx, scy;
    world_to_screen(cx, cy, scx, scy);

    double a_px = a * ppm;
    double b_px = b * ppm;
    double max_r_px = std::max(a_px, b_px) + 2.0;
    int bound = static_cast<int>(std::ceil(max_r_px));

    double cos_t = std::cos(-theta); // screen y is inverted
    double sin_t = std::sin(-theta);

    for (int dy = -bound; dy <= bound; ++dy) {
        int py = scy + dy;
        if (py < 0 || py >= height) continue;
        for (int dx = -bound; dx <= bound; ++dx) {
            int px = scx + dx;
            if (px < 0 || px >= width) continue;

            // Rotate into body frame
            double lx = cos_t * dx - sin_t * dy;
            double ly = sin_t * dx + cos_t * dy;
            double norm_sq = (lx * lx) / (a_px * a_px) + (ly * ly) / (b_px * b_px);

            if (norm_sq <= 1.0) {
                // If near edge, draw outline
                if (norm_sq >= 0.75) {
                    draw_pixel(px, py, outline);
                } else {
                    draw_pixel(px, py, fill);
                }
            }
        }
    }

    // Draw orientation axis indicator
    double dir_x = a * std::cos(theta);
    double dir_y = a * std::sin(theta);
    int end_sx, end_sy;
    world_to_screen(cx + dir_x, cy + dir_y, end_sx, end_sy);
    draw_line(scx, scy, end_sx, end_sy, {255, 60, 60, 255}, 2);
}

void SoftwareRenderer::draw_string(int sx, int sy, const std::string& text, ColorRGBA color, int scale) {
    int cur_x = sx;
    for (char ch : text) {
        if (ch < 32 || ch > 126) ch = ' ';
        int char_idx = ch - 32;

        for (int col = 0; col < 5; ++col) {
            uint8_t line = font5x7[char_idx][col];
            for (int row = 0; row < 7; ++row) {
                if ((line >> row) & 1) {
                    for (int dy = 0; dy < scale; ++dy) {
                        for (int dx = 0; dx < scale; ++dx) {
                            draw_pixel(cur_x + col * scale + dx, sy + row * scale + dy, color);
                        }
                    }
                }
            }
        }
        cur_x += 6 * scale; // 5 font width + 1 spacing
    }
}

ColorRGBA SoftwareRenderer::speed_to_color(double speed, double max_speed) {
    if (max_speed <= 1e-6) max_speed = 0.5;
    double t = std::clamp(speed / max_speed, 0.0, 1.0);

    // Sebastian Lague fluid ramp: Deep Blue -> Cyan -> Teal -> Coral Orange
    if (t < 0.33) {
        double f = t / 0.33;
        uint8_t r = static_cast<uint8_t>(20 + f * (40 - 20));
        uint8_t g = static_cast<uint8_t>(50 + f * (180 - 50));
        uint8_t b = static_cast<uint8_t>(120 + f * (220 - 120));
        return {r, g, b, 230};
    } else if (t < 0.66) {
        double f = (t - 0.33) / 0.33;
        uint8_t r = static_cast<uint8_t>(40 + f * (70 - 40));
        uint8_t g = static_cast<uint8_t>(180 + f * (210 - 180));
        uint8_t b = static_cast<uint8_t>(220 + f * (140 - 220));
        return {r, g, b, 240};
    } else {
        double f = (t - 0.66) / 0.34;
        uint8_t r = static_cast<uint8_t>(70 + f * (245 - 70));
        uint8_t g = static_cast<uint8_t>(210 + f * (100 - 210));
        uint8_t b = static_cast<uint8_t>(140 + f * (40 - 140));
        return {r, g, b, 255};
    }
}

ColorRGBA SoftwareRenderer::vorticity_to_color(double omega_z, double max_vort) {
    if (max_vort <= 1e-6) max_vort = 50.0;
    double norm = std::clamp(omega_z / max_vort, -1.0, 1.0);

    // Diverging: Crimson (-1) -> Pure White (0) -> Deep Navy (+1)
    if (norm < 0.0) {
        double f = -norm; // 0 to 1
        uint8_t r = static_cast<uint8_t>(245 - f * (245 - 200));
        uint8_t g = static_cast<uint8_t>(245 - f * (245 - 35));
        uint8_t b = static_cast<uint8_t>(245 - f * (245 - 50));
        return {r, g, b, static_cast<uint8_t>(180 + f * 75)};
    } else {
        double f = norm; // 0 to 1
        uint8_t r = static_cast<uint8_t>(245 - f * (245 - 25));
        uint8_t g = static_cast<uint8_t>(245 - f * (245 - 60));
        uint8_t b = static_cast<uint8_t>(245 - f * (245 - 160));
        return {r, g, b, static_cast<uint8_t>(180 + f * 75)};
    }
}

void SoftwareRenderer::render_sph_frame(const SPHSolver& solver,
                                        const std::string& mode_label,
                                        const std::string& color_mode,
                                        double max_field_val) {
    clear({255, 255, 255, 255}); // Clean white canvas

    // 1. Draw subtle grid / tank walls
    int left_sx, bottom_sy, right_sx, top_sy;
    world_to_screen(solver.domain_cfg.x_min, solver.domain_cfg.y_min, left_sx, bottom_sy);
    world_to_screen(solver.domain_cfg.x_max, solver.domain_cfg.y_max, right_sx, top_sy);

    ColorRGBA wall_color{30, 36, 48, 255}; // #1E2430
    draw_line(left_sx, top_sy, left_sx, bottom_sy, wall_color, 3);
    draw_line(right_sx, top_sy, right_sx, bottom_sy, wall_color, 3);
    draw_line(left_sx, bottom_sy, right_sx, bottom_sy, wall_color, 3);

    // 2. Draw Fluid Particles
    double particle_r = 0.55 * solver.sph_cfg.dx;
    for (const auto& p : solver.fluid_particles) {
        ColorRGBA c;
        if (color_mode == "vorticity") {
            c = vorticity_to_color(p.vorticity, max_field_val);
        } else {
            c = speed_to_color(p.vel.length(), max_field_val);
        }
        draw_circle_aa(p.pos.x, p.pos.y, particle_r, c);
    }

    // 3. Draw Coin Trail and Coin
    for (const auto& rb : solver.rigid_bodies) {
        // Record trail
        coin_trail.push_back(rb.pos);
        if (coin_trail.size() > 500) {
            coin_trail.erase(coin_trail.begin());
        }

        // Draw trail dots
        for (size_t ti = 0; ti < coin_trail.size(); ti += 4) {
            int tsx, tsy;
            world_to_screen(coin_trail[ti].x, coin_trail[ti].y, tsx, tsy);
            draw_pixel(tsx, tsy, {150, 160, 175, 200});
        }

        // Draw coin ellipse
        ColorRGBA coin_fill{34, 40, 49, 255};    // #222831
        ColorRGBA coin_outline{17, 17, 17, 255}; // #111111
        draw_ellipse(rb.pos.x, rb.pos.y, rb.config.a(), rb.config.b(), rb.theta, coin_fill, coin_outline);
    }

    // 4. Draw HUD Header Bar
    // Top header background
    for (int y = 0; y < 80; ++y) {
        for (int x = 0; x < width; ++x) {
            draw_pixel(x, y, {248, 249, 250, 240});
        }
    }
    draw_line(0, 80, width, 80, {220, 224, 230, 255}, 2);

    // Mode label
    draw_string(20, 15, mode_label, {17, 24, 39, 255}, 2);

    // Live Metrics HUD
    if (!solver.rigid_bodies.empty()) {
        const auto& coin = solver.rigid_bodies[0];
        std::ostringstream ss;
        ss << std::fixed << std::setprecision(3);
        ss << "t: " << solver.sim_time << " s | I*: " << coin.config.I_star()
           << " | Re_in: " << static_cast<int>(std::round(coin.config.U_t() * coin.config.L / solver.fluid_cfg.nu()))
           << " | theta: " << std::setprecision(1) << (coin.theta * 180.0 / M_PI) << " deg"
           << " | Y: " << std::setprecision(3) << coin.pos.y << " m";
        draw_string(20, 45, ss.str(), {75, 85, 99, 255}, 2);
    }
}

void SoftwareRenderer::render_ode_replay_frame(const Vec2& coin_pos,
                                               double theta,
                                               double L,
                                               double h,
                                               double t,
                                               double I_star,
                                               double Re_meas,
                                               const std::string& regime_label) {
    clear({255, 255, 255, 255});

    // Trail
    coin_trail.push_back(coin_pos);
    if (coin_trail.size() > 500) coin_trail.erase(coin_trail.begin());
    for (size_t ti = 0; ti < coin_trail.size(); ti += 3) {
        int tsx, tsy;
        world_to_screen(coin_trail[ti].x, coin_trail[ti].y, tsx, tsy);
        draw_pixel(tsx, tsy, {120, 130, 150, 220});
    }

    // Coin
    ColorRGBA coin_fill{34, 40, 49, 255};
    ColorRGBA coin_outline{17, 17, 17, 255};
    draw_ellipse(coin_pos.x, coin_pos.y, L * 0.5, h * 0.5, theta, coin_fill, coin_outline);

    // HUD Bar
    for (int y = 0; y < 80; ++y) {
        for (int x = 0; x < width; ++x) {
            draw_pixel(x, y, {248, 249, 250, 240});
        }
    }
    draw_line(0, 80, width, 80, {220, 224, 230, 255}, 2);

    draw_string(20, 15, "2D ODE simulation replay - visualization only", {17, 24, 39, 255}, 2);

    std::ostringstream ss;
    ss << std::fixed << std::setprecision(3);
    ss << "t: " << t << " s | I*: " << I_star
       << " | Re_meas: " << static_cast<int>(std::round(Re_meas))
       << " | theta: " << std::setprecision(1) << (theta * 180.0 / M_PI) << " deg"
       << " | Regime: " << regime_label;
    draw_string(20, 45, ss.str(), {75, 85, 99, 255}, 2);
}

bool SoftwareRenderer::save_png(const std::string& filepath) const {
    // 4 channels (RGBA), stride is width * 4
    int res = stbi_write_png(filepath.c_str(), width, height, 4, pixels.data(), width * 4);
    return res != 0;
}

} // namespace sph
