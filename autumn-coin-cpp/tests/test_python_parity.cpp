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
}
