#include "doctest.h"
#include "autumn/model.hpp"
#include "autumn/integrator.hpp"
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <cmath>

using namespace autumn;

struct RefRow {
    double t;
    State state;
};

static std::vector<RefRow> load_reference_csv(const std::string& path) {
    std::vector<RefRow> rows;
    std::ifstream ifs(path);
    if (!ifs.is_open()) return rows;

    std::string line;
    std::getline(ifs, line); // header

    while (std::getline(ifs, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::string val;
        RefRow r;
        std::getline(ss, val, ','); r.t = std::stod(val);
        for (int i = 0; i < 6; ++i) {
            std::getline(ss, val, ',');
            r.state[i] = std::stod(val);
        }
        rows.push_back(r);
    }
    return rows;
}

static std::vector<RefRow> load_reference_file(const std::string& filename) {
    std::vector<std::string> search_paths = {
        filename,
        "tests/reference/" + filename,
        "../tests/reference/" + filename,
        "../../tests/reference/" + filename,
        "autumn-coin-cpp/tests/reference/" + filename,
        "../autumn-coin-cpp/tests/reference/" + filename,
        "D:/Autumn coin/autumn-coin-cpp/tests/reference/" + filename
    };
    for (const auto& p : search_paths) {
        auto r = load_reference_csv(p);
        if (!r.empty()) return r;
    }
    return {};
}

TEST_CASE("Test 1: Python Parity Verification across Presets") {
    // 1. Reference Card at 5 deg
    {
        PlateConfig p;
        p.L = 0.020;
        p.h = 0.0015;
        p.rho_s = 9000.0;
        FluidConfig f;
        CoeffsConfig c;
        Model m(p, f, c);

        auto ref = load_reference_file("ref_reference_card_th5.csv");
        REQUIRE(!ref.empty());

        State s = ref[0].state;
        double t = ref[0].t;
        double dt = 1e-4;

        double max_pos_err = 0.0;
        double max_th_err = 0.0;

        size_t ref_idx = 1;
        while (ref_idx < ref.size()) {
            s = rk4_step(m, t, s, dt);
            t += dt;

            if (std::abs(t - ref[ref_idx].t) < 0.5 * dt) {
                double pos_err = std::hypot(s[0] - ref[ref_idx].state[0], s[1] - ref[ref_idx].state[1]);
                double th_err = std::abs(s[2] - ref[ref_idx].state[2]);
                max_pos_err = std::max(max_pos_err, pos_err);
                max_th_err = std::max(max_th_err, th_err);
                ref_idx++;
            }
        }

        // Must match Python within tight tolerance
        CHECK(max_pos_err < 1e-5);
        CHECK(max_th_err < 1e-5);
    }

    // 2. Heavy Coin at 45 deg
    {
        PlateConfig p;
        p.L = 0.024;
        p.h = 0.0018;
        p.rho_s = 7800.0;
        FluidConfig f;
        CoeffsConfig c;
        Model m(p, f, c);

        auto ref = load_reference_file("ref_heavy_coin_th45.csv");
        REQUIRE(!ref.empty());

        State s = ref[0].state;
        double t = ref[0].t;
        double dt = 1e-4;

        double max_pos_err = 0.0;
        size_t ref_idx = 1;
        while (ref_idx < ref.size()) {
            s = rk4_step(m, t, s, dt);
            t += dt;

            if (std::abs(t - ref[ref_idx].t) < 0.5 * dt) {
                double pos_err = std::hypot(s[0] - ref[ref_idx].state[0], s[1] - ref[ref_idx].state[1]);
                max_pos_err = std::max(max_pos_err, pos_err);
                ref_idx++;
            }
        }

        CHECK(max_pos_err < 1e-5);
    }

    // 3. Steady Card at 10 deg
    {
        PlateConfig p;
        p.L = 0.020;
        p.h = 0.002;
        p.rho_s = 1200.0;
        FluidConfig f;
        CoeffsConfig c;
        Model m(p, f, c);

        auto ref = load_reference_file("ref_steady_card_th10.csv");
        REQUIRE(!ref.empty());

        State s = ref[0].state;
        double t = ref[0].t;
        double dt = 1e-4;

        double max_pos_err = 0.0;
        size_t ref_idx = 1;
        while (ref_idx < ref.size()) {
            s = rk4_step(m, t, s, dt);
            t += dt;

            if (std::abs(t - ref[ref_idx].t) < 0.5 * dt) {
                double pos_err = std::hypot(s[0] - ref[ref_idx].state[0], s[1] - ref[ref_idx].state[1]);
                max_pos_err = std::max(max_pos_err, pos_err);
                ref_idx++;
            }
        }

        CHECK(max_pos_err < 1e-5);
    }

    // 4. Light Coin at 30 deg
    {
        PlateConfig p;
        p.L = 0.024;
        p.h = 0.0018;
        p.rho_s = 2700.0;
        FluidConfig f;
        CoeffsConfig c;
        Model m(p, f, c);

        auto ref = load_reference_file("ref_light_coin_th30.csv");
        REQUIRE(!ref.empty());

        State s = ref[0].state;
        double t = ref[0].t;
        double dt = 1e-4;

        double max_pos_err = 0.0;
        size_t ref_idx = 1;
        while (ref_idx < ref.size()) {
            s = rk4_step(m, t, s, dt);
            t += dt;

            if (std::abs(t - ref[ref_idx].t) < 0.5 * dt) {
                double pos_err = std::hypot(s[0] - ref[ref_idx].state[0], s[1] - ref[ref_idx].state[1]);
                max_pos_err = std::max(max_pos_err, pos_err);
                ref_idx++;
            }
        }

        CHECK(max_pos_err < 1e-5);
    }
}

TEST_CASE("Test 10: Three Reference Benchmark Cases Reproduction (I* = 1.1, 1.4, 1.6)") {
    FluidConfig f;
    f.rho_f = 998.0;
    f.g = 9.81;
    CoeffsConfig c;
    c.mu_1 = 0.2;
    c.mu_2 = 0.2;
    c.C_tau = M_PI * 0.2 / 8.0;

    double L = 0.024;
    double a = 0.5 * L;
    double h = 0.01 * L; // Thin plate limit
    double b = 0.5 * h;

    struct Case {
        double I_star;
        double x_ref;
        double y_ref;
    };

    Case cases[] = {
        {1.1, 7.3, -33.0},
        {1.4, -26.1, -24.3},
        {1.6, 6.1, -29.3}
    };

    for (const auto& cs : cases) {
        PlateConfig p;
        p.L = L;
        p.h = h;
        p.rho_s = cs.I_star * f.rho_f * L / h;

        Model m(p, f, c);

        double U = std::sqrt(std::max(p.rho_s / f.rho_f - 1.0, 0.0) * f.g * b);
        double t_end = 50.0 * (a / U);
        double dt = 1e-4;

        State s = {0.0, 0.0, 0.1, 0.0, -U, 0.0};
        double t = 0.0;
        int steps = static_cast<int>(std::round(t_end / dt));
        for (int i = 0; i < steps; ++i) {
            s = rk4_step(m, t, s, dt);
            t += dt;
        }

        double x_a = s[0] / a;
        double y_a = s[1] / a;

        CHECK(std::abs(x_a - cs.x_ref) < 0.3);
        CHECK(std::abs(y_a - cs.y_ref) < 0.3);
    }
}
